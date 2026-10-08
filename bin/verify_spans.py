"""Mechanical span-contract verification for local-tier summaries.

Every claim in a local summary must carry `source_spans`: exact, verbatim,
contiguous quotes from the raw source text. This module checks each span
with a strict substring match against the source. Any failure — hallucinated
span, paraphrased span, truncated span, empty/missing spans — fails CLOSED.

Used two ways:
 1. Imported by bin/local_summarize.py as a post-model gate (exit 2).
 2. CLI: verify_spans.py --source-file PATH < doc.json -> exit 0/2.

Honest limits: substring existence is grounding of the SPAN, not entailment
of the CLAIM by the span. A span can exist verbatim yet not support the
claim's inference. That gap stays on hand review + the qualifier gate.
What this kills mechanically: invented quotes, paraphrase drift, truncation.
"""

import argparse
import json
import re
import sys

MIN_SPAN_LEN = 10  # degenerate spans ("a", "8") prove nothing; fail them


def strip_fences(text: str) -> str:
    """Remove markdown code fences the model may wrap around the JSON."""
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", t, re.DOTALL)
    return m.group(1).strip() if m else t


def parse_doc(text: str):
    """Parse model output into a dict; return None on any failure."""
    try:
        doc = json.loads(strip_fences(text))
    except (json.JSONDecodeError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def verify(source: str, doc: dict) -> list:
    """Return the list of span-contract failures ([] = contract holds)."""
    if not isinstance(doc, dict):
        return ["doc is not a JSON object"]
    if not isinstance(source, str) or not source:
        return ["source empty"]
    claims = doc.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["claims missing or empty"]
    failures = []
    for i, c in enumerate(claims):
        if not isinstance(c, dict):
            failures.append(f"claim[{i}] is not an object")
            continue
        claim = c.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            failures.append(f"claim[{i}].claim missing or empty")
        spans = c.get("source_spans")
        if not isinstance(spans, list) or not spans:
            failures.append(f"claim[{i}].source_spans missing or empty")
            continue
        for j, s in enumerate(spans):
            loc = f"claim[{i}].source_spans[{j}]"
            if not isinstance(s, str) or not s.strip():
                failures.append(f"{loc} empty")
                continue
            if len(s) < MIN_SPAN_LEN:
                failures.append(
                    f"{loc} too short ({len(s)}<{MIN_SPAN_LEN}): {s[:40]!r}")
                continue
            if s not in source:
                failures.append(f"{loc} not verbatim in source: {s[:60]!r}")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify span-contract: every source_spans entry must "
                    "exist verbatim in the source. Doc JSON on stdin.")
    ap.add_argument("--source-file", required=True,
                    help="path to the raw source text file")
    args = ap.parse_args()
    with open(args.source_file) as f:
        source = f.read()
    doc = parse_doc(sys.stdin.read())
    if doc is None:
        print("span_verify: FAIL — output is not parseable JSON",
              file=sys.stderr)
        return 2
    failures = verify(source, doc)
    if failures:
        print(f"span_verify: FAIL — {len(failures)} span violation(s)",
              file=sys.stderr)
        for fl in failures[:10]:
            print(f"  - {fl}", file=sys.stderr)
        return 2
    n_spans = sum(len(c.get("source_spans", []))
                  for c in doc["claims"] if isinstance(c, dict))
    print(f"span_verify: OK — {len(doc['claims'])} claims, "
          f"{n_spans} spans, all verbatim in source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
