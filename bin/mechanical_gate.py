#!/usr/bin/env python3
"""Reform 3: the consolidated mechanical gate for the local inference tier.

Replaces the discarded 0.85 confidence actuator. The gate decides
PASS / ESCALATE on deterministic checks ONLY.

The model's self-reported `confidence` field is accepted in the schema but
is NEVER read by the decision function — it is write-only telemetry.
Confidence is inert by construction, not by convention. The adversarial
tests in bin/test_mechanical_gate.py prove this: a 0.97-confidence
hallucination is rejected and a 0.31-confidence grounded output passes —
the gate is structurally blind to the model's internal confidence scores.

Checks (ALL must pass; any failure -> ESCALATE):
  1. schema      valid JSON object; "claims" is a list of {"claim": str,
                 "source_spans": [str, ...]}; claim non-empty; spans non-empty.
                 "confidence" may be present in any form — it is not read.
  2. spans       every source_spans string is a verbatim substring of the
                 source and >= 10 chars (reuses bin/verify_spans.verify —
                 kills fabrication, quote drift, interior deletion).
  3. qualifiers  epistemic families present in the source (unverified,
                 single-report, rumor, alleged) are preserved in the joined
                 claims text (reuses local_summarize.qualifier_gate —
                 kills epistemic erosion).
  4. provenance  "provenance" key present and sha-bound to the body
                 (reuses provenance.verify_json_object — accepts both
                 tier=local and tier=local_cpu_fallback).
  5. heartbeat   if a heartbeat path is asserted (--assert-path), it must be
                 in the closed 7-path vocabulary (guards against invented
                 telemetry paths).

Exit codes:
  0  PASS — output usable as local-tier advisory
  2  ESCALATE — caller reads raw; confidence could neither save nor kill it
  1  usage / input error (not a gate verdict)

Honest limit (carried from reform 2): substring existence grounds the SPAN,
not claim entailment. A verbatim span can still fail to support its claim's
inference. The gate kills fabrication and epistemic decay, not false
inference from true quotes — that residual stays on hand review.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provenance  # noqa: E402
import verify_spans  # noqa: E402
from epistemic import qualifier_gate  # noqa: E402  (bin/epistemic.py, leaf module)

HEARTBEAT_PATHS = {
    "llm_ok", "llm_transport_failed", "llm_bad_output", "gate_refused",
    "gpu_busy_yield", "guard_unreachable_yield", "skipped_no_input",
}

# --- Pinned JSON schemas (canary/pins reform) ---
# The contracts the local tier's outputs must satisfy. SPAN_CONTRACT_SCHEMA
# is ENFORCED by check_schema() below (the gate validates against this
# constant — it is not documentation). TRIAGE_SCHEMA is the documented
# contract for the triage output shape (digit keys -> ticker arrays, plus
# the provenance key); the triage script enforces it via its clean-and-filter
# pass. SHA-256 of both constants is recorded in hidden_files/pins.json.
# NOTE: "confidence" is deliberately absent from the claim properties: it is
# accepted in any form and never inspected — making it schema-load-bearing
# would let a malformed confidence string kill an otherwise good summary.
SPAN_CONTRACT_SCHEMA = {
    "type": "object",
    "required": ["claims"],
    "properties": {
        "claims": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["claim", "source_spans"],
                "properties": {
                    "claim": {"type": "string", "minLength": 1,
                              "pattern": "\\S"},
                    "source_spans": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
        "provenance": {"type": "object"},
    },
}

TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "provenance": {"type": "object"},
    },
    "patternProperties": {
        "^[0-9]+$": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


def _validate(doc, schema: dict, path: str = "$") -> list:
    """Minimal pure-stdlib JSON-schema-subset validator.

    Supports exactly the keywords used above: type, required, properties,
    patternProperties, items, minLength, minItems, pattern. Returns a list of
    violation strings (empty = conforms). Unknown keywords are ignored;
    unknown properties are allowed.
    """
    bad = []
    t = schema.get("type")
    if t == "object":
        if not isinstance(doc, dict):
            return [f"{path}: expected object, got {type(doc).__name__}"]
        for req in schema.get("required", []):
            if req not in doc:
                bad.append(f"{path}: required property '{req}' missing")
        props = schema.get("properties", {})
        pats = schema.get("patternProperties", {})
        for key, val in doc.items():
            sub = props.get(key)
            if sub is None:
                for pat, pschema in pats.items():
                    if re.match(pat, key):
                        sub = pschema
                        break
            if sub is not None:
                bad.extend(_validate(val, sub, f"{path}.{key}"))
    elif t == "array":
        if not isinstance(doc, list):
            return [f"{path}: expected array, got {type(doc).__name__}"]
        if len(doc) < schema.get("minItems", 0):
            bad.append(f"{path}: array too short "
                       f"(min {schema['minItems']}, got {len(doc)})")
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(doc):
                bad.extend(_validate(item, item_schema, f"{path}[{i}]"))
    elif t == "string":
        if not isinstance(doc, str):
            bad.append(f"{path}: expected string, got {type(doc).__name__}")
        else:
            if len(doc) < schema.get("minLength", 0):
                bad.append(f"{path}: string too short "
                           f"(min {schema['minLength']})")
            pat = schema.get("pattern")
            if pat is not None and not re.search(pat, doc):
                bad.append(f"{path}: string does not match pattern")
    elif t == "number":
        if not isinstance(doc, (int, float)) or isinstance(doc, bool):
            bad.append(f"{path}: expected number, got {type(doc).__name__}")
    return bad


def check_schema(doc) -> list:
    """Return a list of schema violations (empty = conforms).

    Validates against the pinned SPAN_CONTRACT_SCHEMA — the constant IS the
    enforcement. "confidence" is deliberately never inspected here.
    """
    return _validate(doc, SPAN_CONTRACT_SCHEMA)


def gate(source: str, doc: dict, assert_path: str = None) -> tuple:
    """Run the consolidated mechanical checklist.

    Returns (passed: bool, failures: [str]). The decision function reads
    spans, qualifiers, provenance, and schema — never confidence, never
    multi-sample agreement (agreement is benched offline as an annotation
    only; this function takes no samples parameter by design).
    """
    failures = []

    failures.extend(f"schema: {v}" for v in check_schema(doc))
    if failures:
        # Span/qualifier checks need a well-formed doc; fail fast.
        return False, failures

    for v in verify_spans.verify(source, doc):
        failures.append(f"spans: {v}")

    claims_text = " ".join(c["claim"] for c in doc["claims"]
                           if isinstance(c, dict))
    for fam in qualifier_gate(source, claims_text):
        failures.append(f"qualifiers: source family '{fam}' dropped in claims")

    if not provenance.verify_json_object(doc):
        failures.append("provenance: missing, wrong tier, or sha mismatch")

    if assert_path is not None and assert_path not in HEARTBEAT_PATHS:
        failures.append(f"heartbeat: path '{assert_path}' not in closed vocabulary")

    return (not failures), failures


def main() -> int:
    ap = argparse.ArgumentParser(description="Reform 3 mechanical gate")
    ap.add_argument("--source-file", required=True)
    ap.add_argument("--doc-file", required=True,
                    help="JSON span-contract doc to gate")
    ap.add_argument("--assert-path", default=None,
                    help="heartbeat path the caller asserts; must be in vocabulary")
    a = ap.parse_args()
    try:
        source = open(a.source_file).read()
        doc = json.load(open(a.doc_file))
    except (OSError, json.JSONDecodeError) as e:
        print(f"gate: INPUT ERROR — {e}", file=sys.stderr)
        return 1
    passed, failures = gate(source, doc, a.assert_path)
    if passed:
        print("gate: PASS — all mechanical checks held", file=sys.stderr)
        return 0
    print("gate: ESCALATE — caller reads raw", file=sys.stderr)
    for f in failures:
        print(f"gate:   - {f}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
