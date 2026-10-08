#!/usr/bin/env python3
"""trip_doctrines.py — mechanical circuit breaker for doctrine kill triggers.

Runs in step-0 immediately after audit_doctrines.py, every cycle.

Scans proposals/pending/ for NEW kill-class proposals on the risk-path
doctrines (D-001, D-003, D-004 — CODE-enforced in the shared book_trade.py
choke point) and records their ids in hidden_files/doctrine.trip.
book_trade.py refuses new risk (book/shadow/bootstrap, exit 4) while that
file is non-empty; `exit` stays live (flatten, don't freeze).

Scoping (Gabe-approved 2026-09-26 ~04:33 CDT):
- Only kill-class proposals on D-001/D-003/D-004 trip. Governance filings
  (D-002 cap, liturgy silence tripwires, review revisit-dues) endanger no
  capital and stay loud-but-manual — the machine does not flinch at
  paperwork.
- Only MECHANICAL measurements trip. MANUAL triggers and R kill-notes file
  proposals; a mind adjudicates. Advisory nodes never get a hard veto.

Asymmetric clearance: this script (and the worker) may WRITE the trip file;
only K3N1 or Gabe clears it — after adjudicating the proposal
(reaffirm/revise/retire), fixing the enforcement, and logging the
resolution EVENT:. The worker never clears its own trip.

Idempotent: re-running appends nothing new. Exit 0 always — this is state
maintenance, not violation reporting (the audit already reported via
exit 2); trip events print LOUD to stdout for the step-0 log.
"""
import glob
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

CDT = ZoneInfo("America/Chicago")
ROOT = os.path.expanduser("~/workspace/goals/10-polymarket-experiment")
PENDING = os.path.join(ROOT, "proposals", "pending")
TRIP_FILE = os.path.join(ROOT, "hidden_files", "doctrine.trip")

RISK_DOCTRINES = {"D-001", "D-003", "D-004"}
KILL_TYPE = "doctrine-kill"


def tripped_ids():
    try:
        with open(TRIP_FILE) as f:
            return {line.split()[0] for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def main():
    already = tripped_ids()
    new = []
    for path in sorted(glob.glob(os.path.join(PENDING, "*.json"))):
        try:
            with open(path) as f:
                p = json.load(f)
        except (OSError, ValueError):
            continue
        pid = p.get("id", "")
        if (p.get("type") == KILL_TYPE
                and p.get("doctrine_id") in RISK_DOCTRINES
                and pid and pid not in already):
            new.append(pid)
    if new:
        stamp = datetime.now(CDT).strftime("%Y-%m-%d %H:%M %Z")
        os.makedirs(os.path.dirname(TRIP_FILE), exist_ok=True)
        with open(TRIP_FILE, "a") as f:
            for pid in new:
                f.write(f"{pid} {stamp}\n")
                print(f"DOCTRINE TRIP: {pid} — new risk severed, exits live")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
