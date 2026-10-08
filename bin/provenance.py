"""Immutable provenance tags for the local inference tier.

Every output produced by the local tier (gdesk / Ollama) carries a
provenance tag binding it to its origin. The booking choke point in
book_trade.py reads these tags: a payload bearing local provenance is
refused on the real-money `book` path (exit 4, mechanical) while remaining
eligible for the paper `shadow` path. That is the structural isolation:
local tier -> paper freely, local tier -> money never.

Two tag forms:
 text: [PROVENANCE tier=local host=gdesk model=qwen2.5:14b
 tool=local_summarize ts=<iso> sha=<32 hex>]
 prepended as the first line of plain-text output. sha binds the tag
 to the content that follows (tamper-evident).
 json: {"provenance": {"tier": "local", "host": ..., "model": ...,
 "tool": ..., "ts": ..., "sha": ...}}
 merged into JSON output. sha binds to the canonical serialization
 of the object minus the provenance key.

Tier vocabulary (closed):
 "local" — LLM output from the gdesk Ollama tier
 "local_cpu_fallback" — non-LLM CPU baseline (bin/cpu_fallback.py) emitted
 on GPU-guard yield. Degraded cycles are explicitly
 tracked and never conflated with qwen2.5:14b runs.
Both tiers are refused on the real-money path; both are paper-eligible.

Threat model (honest limits):
 - Forging a tag only causes refusal: fail-closed, safe direction.
 - Stripping a tag defeats detection: this is a cooperative marker, not
 a cryptographic guarantee against an adversary rewriting the payload.
 The pipeline's own scripts are required to emit it; the 30-day tier
 review ledger tracks what the local tier decided.
 - Detection scans every string field of the booking command, so tagged
 content smuggled through --thesis, --note, --market, etc. is caught.
"""

import hashlib
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

CDT = ZoneInfo("America/Chicago")
HOST = "gdesk"
TIER = "local"
CPU_TIER = "local_cpu_fallback"
_LOCAL_TIERS = (TIER, CPU_TIER)


def _check_tier(tier: str) -> str:
    if tier not in _LOCAL_TIERS:
        raise ValueError(f"unknown provenance tier: {tier!r}")
    return tier


# Text form: [PROVENANCE tier=local[_cpu_fallback] host=... ...]
TEXT_TAG_RE = re.compile(
    r"\[PROVENANCE\s+tier=local(?:_cpu_fallback)?(?:\s+[a-z_]+=[^\s\]]+)*\]"
)
# JSON form: "provenance": { ... "tier": "local[_cpu_fallback]" ... }
JSON_TAG_RE = re.compile(
    r'"provenance"\s*:\s*\{[^}]*"tier"\s*:\s*"local(?:_cpu_fallback)?"'
)

_MONEY_CMDS = ("book",)  # real-money path; shadow/bootstrap are paper/ops


def _ts() -> str:
    return datetime.now(CDT).isoformat(timespec="seconds")


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def emit_text_tag(tool: str, model: str, content: str,
                  host: str = HOST, tier: str = TIER) -> str:
    """Build the text-form tag bound to `content` (content AFTER the tag)."""
    _check_tier(tier)
    return (f"[PROVENANCE tier={tier} host={host} model={model} "
            f"tool={tool} ts={_ts()} sha={_sha(content)}]")


def tag_text(tool: str, model: str, content: str, host: str = HOST,
             tier: str = TIER) -> str:
    """Prepend a provenance tag to plain-text local-tier output."""
    return emit_text_tag(tool, model, content, host, tier) + "\n" + content


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def tag_json_object(tool: str, model: str, obj: dict,
                    host: str = HOST, tier: str = TIER) -> dict:
    """Return a copy of obj with a content-bound provenance key merged in."""
    _check_tier(tier)
    body = dict(obj)
    body.pop("provenance", None)
    out = dict(body)
    out["provenance"] = {
        "tier": tier,
        "host": host,
        "model": model,
        "tool": tool,
        "ts": _ts(),
        "sha": _sha(_canonical(body)),
    }
    return out


def extract_text_tag(text: str):
    """Parse the text-form tag; return field dict or None."""
    m = TEXT_TAG_RE.search(text)
    if not m:
        return None
    fields = {}
    for kv in m.group(0)[1:-1].split()[1:]:  # skip "[PROVENANCE"
        if "=" in kv:
            k, v = kv.split("=", 1)
            fields[k] = v
    return fields


def verify_text_tag(tagged: str) -> bool:
    """True iff the tag binds to the content that follows it."""
    lines = tagged.split("\n", 1)
    if len(lines) != 2:
        return False
    fields = extract_text_tag(lines[0])
    if not fields or fields.get("tier") not in _LOCAL_TIERS:
        return False
    return fields.get("sha") == _sha(lines[1])


def verify_json_object(obj: dict) -> bool:
    """True iff the provenance key binds to the rest of the object."""
    prov = obj.get("provenance")
    if not isinstance(prov, dict) or prov.get("tier") not in _LOCAL_TIERS:
        return False
    body = {k: v for k, v in obj.items() if k != "provenance"}
    return prov.get("sha") == _sha(_canonical(body))


def has_local_provenance(*fields) -> bool:
    """True iff any string field carries a local-tier provenance tag."""
    for f in fields:
        if not isinstance(f, str):
            continue
        if TEXT_TAG_RE.search(f) or JSON_TAG_RE.search(f):
            return True
    return False


def should_refuse(cmd: str, *fields) -> bool:
    """Mechanical booking-path rule: local provenance + money path = refuse."""
    return cmd in _MONEY_CMDS and has_local_provenance(*fields)
