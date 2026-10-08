#!/usr/bin/env python3
"""Mechanical bar registration gate — bin/register_bar.py.

New kill conditions and metric bars are registered through this script, not
by prose edits. It enforces the two pre-registered requirements from SPEC.md:
  1. Evaluability gate: --proof must be an executable test demonstrating each
     clause can both trip and clear. The script RUNS it; non-zero exit ->
     REFUSED. (The script enforces existence + green; the proof's content —
     asserting trip AND clear — is the author's job, audited in review.)
  2. Judgment log: hidden_files/judgment_log.jsonl must contain an entry with
     bar_id == --bar-id, carrying a confidence value and a mandatory wrong_if.

Either missing -> print REFUSED with reasons, exit 2, nothing is registered.
On success the bar record is appended to hidden_files/bar_registry.jsonl.

A gate that has never been seen to refuse something is unverified:
bin/test_register_bar.py attempts registration without a log entry (and with
a failing proof, and without wrong_if) and asserts refusal in each case.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(ROOT, "hidden_files", "bar_registry.jsonl")
DEFAULT_JLOG = os.path.join(ROOT, "hidden_files", "judgment_log.jsonl")
PROOF_TIMEOUT_S = 120


def fail(*reasons):
    print("REFUSED: " + "; ".join(reasons))
    return 2


def load_jlog(path):
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


_DATE_RE = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")


def wrong_if_dates_ok(entry):
    """A wrong_if naming a date earlier than the entry's own timestamp is a
    slip (2026-10-06 + 90d was once written 2026-01-04 instead of
    2027-01-04). ISO dates compare lexicographically. Returns (ok, bad_date).
    """
    ts_day = (entry.get("ts_cdt") or "")[:10]
    for m in _DATE_RE.finditer(entry.get("wrong_if") or ""):
        if m.group(0) < ts_day:
            return False, m.group(0)
    return True, None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bar-id", required=True)
    ap.add_argument("--spec", required=True, help="path to the bar's spec text")
    ap.add_argument("--proof", required=True, help="executable trip/clear proof test")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--judgment-log", default=DEFAULT_JLOG)
    a = ap.parse_args(argv)

    reasons = []
    bid = a.bar_id.strip()
    if not bid or any(c.isspace() for c in bid):
        reasons.append("bar-id must be a non-empty token without whitespace")

    if not (a.spec and os.path.isfile(a.spec) and os.path.getsize(a.spec) > 0):
        reasons.append("spec file missing or empty: %s" % a.spec)

    if not (a.proof and os.path.isfile(a.proof)):
        reasons.append("proof file missing: %s" % a.proof)
    else:
        try:
            r = subprocess.run([sys.executable, a.proof],
                               capture_output=True, text=True,
                               timeout=PROOF_TIMEOUT_S)
            if r.returncode != 0:
                reasons.append("proof test failed (exit %d): %s"
                               % (r.returncode, (r.stdout + r.stderr)[-300:]))
        except subprocess.TimeoutExpired:
            reasons.append("proof test timed out after %ds" % PROOF_TIMEOUT_S)
        except OSError as e:
            reasons.append("proof test could not run: %s" % e)

    try:
        entries = load_jlog(a.judgment_log)
    except (OSError, ValueError) as e:
        entries = []
        reasons.append("judgment log unreadable: %s" % e)
    match = [e for e in entries if e.get("bar_id") == bid]
    if not match:
        reasons.append("no judgment-log entry with bar_id=%r" % bid)
    else:
        e = match[-1]
        if not e.get("wrong_if"):
            reasons.append("judgment-log entry for %r lacks mandatory wrong_if" % bid)
        if e.get("confidence") is None:
            reasons.append("judgment-log entry for %r lacks confidence" % bid)
        if e.get("wrong_if"):
            ok, bad = wrong_if_dates_ok(e)
            if not ok:
                reasons.append(
                    "judgment-log entry for %r: wrong_if names %s, earlier than "
                    "entry date %s" % (bid, bad, (e.get("ts_cdt") or "")[:10]))

    if os.path.exists(a.registry):
        with open(a.registry) as f:
            for line in f:
                line = line.strip()
                if line and json.loads(line).get("bar_id") == bid:
                    reasons.append("bar_id %r already registered" % bid)
                    break

    if reasons:
        return fail(*reasons)

    rec = {"bar_id": bid, "spec": a.spec, "proof": a.proof,
           "registered_by": "register_bar.py",
           "registered_ts_cdt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}
    os.makedirs(os.path.dirname(a.registry), exist_ok=True)
    with open(a.registry, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print("REGISTERED: %s" % bid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
