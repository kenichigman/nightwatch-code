#!/usr/bin/env python3
"""Brier shadow tracker — the scored side of the calibration log.

Two scoring paths feed brier_shadow.json:
 1. pending -> scored: mechanical exits (and settle-filed rows) graded at
 resolution. Rows are filed to "pending" by hand or by
 `book_trade.py settle`; resolve moves them to "scored" when their
 market appears in settled.json.
 2. ledger-direct (repair): book rows held in position whose
 markets settled are scored straight from the JSON ledger's canonical
 win_p. This closes the gap where in-position resolutions never entered
 "pending" (e.g. C's btc80k), leaving the mikiri gate (desk_calibration)
 and calibrate.py blind to graded data the dashboard already showed.

Reads the JSON ledger as the singular source of truth (never PAPER.md —
the projection renders from the ledger, not the reverse).

Usage:
 bin/brier.py # resolve pending + ledger-direct, print summary
 bin/brier.py --json # resolve, print full scored/pending as JSON
 bin/brier.py --read-only # report without resolving/writing
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    CDT = ZoneInfo("America/Chicago")
except Exception:
    CDT = None

ROOT = os.path.expanduser("~/workspace/goals/10-polymarket-experiment")
LEDGER = os.path.join(ROOT, "hidden_files", "book_ledger.jsonl")
SETTLED = os.path.join(ROOT, "hidden_files", "settled.json")
SHADOW = os.path.join(ROOT, "hidden_files", "brier_shadow.json")


def now_cdt():
    if CDT:
        return datetime.now(CDT).strftime("%Y-%m-%d %H:%M CDT")
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def norm_slug(raw):
    """Strip venue suffixes like ' (.com)' so ledger markets match settled keys."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", str(raw or "").strip())


def norm_side(raw):
    return str(raw or "").strip().lower()


def outcome_for(side, settled_entry):
    """outcome=1 if the booked side's contract paid out."""
    yes_won = settled_entry.get("yes_won")
    if yes_won is None:
        return None
    s = norm_side(side)
    if s == "yes":
        return 1 if yes_won else 0
    if s == "no":
        return 0 if yes_won else 1
    return None


def score_key(market, desk, side):
    return (norm_slug(market), str(desk or "").strip().upper(),
            norm_side(side))


def resolve(read_only=False):
    shadow = load_json(SHADOW, {"pending": [], "scored": []})
    settled = load_json(SETTLED, {}).get("settled", {})
    pending = shadow.get("pending", [])
    scored = shadow.get("scored", [])
    scored_keys = {score_key(e.get("market"), e.get("desk"), e.get("side"))
                   for e in scored}
    pending_keys = {score_key(e.get("market"), e.get("desk"), e.get("side"))
                    for e in pending}

    # Path 1: pending -> scored (mechanical exits + settle-filed rows).
    still_pending, n_pending = [], 0
    for e in pending:
        entry = settled.get(norm_slug(e.get("market")))
        outcome = outcome_for(e.get("side"), entry) if entry else None
        if outcome is None or e.get("p") is None:
            still_pending.append(e)
            continue
        scored.append({
            "desk": e["desk"], "market": e["market"], "side": e.get("side"),
            "p": e["p"], "outcome": outcome,
            "brier": round((e["p"] - outcome) ** 2, 4),
            "sen": e.get("sen"),
            "resolved_cdt": entry.get("resolved_cdt"),
            "scored_cdt": now_cdt(),
            "provenance": "pending-shadow",
        })
        scored_keys.add(score_key(e.get("market"), e.get("desk"),
                                  e.get("side")))
        n_pending += 1

    # Path 2: ledger-direct — in-position resolutions from canonical win_p.
    n_direct = 0
    try:
        book_rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
    except OSError:
        book_rows = []
    for b in book_rows:
        if b.get("action") != "book":
            continue
        if b.get("desk") == "X" or b.get("directive"):
            continue  # unscored sandbox / directive rows never grade
        win_p = b.get("win_p")
        if win_p is None:
            continue  # unknown probability — nothing to score
        entry = settled.get(norm_slug(b.get("market")))
        outcome = outcome_for(b.get("side"), entry) if entry else None
        if outcome is None:
            continue
        key = score_key(b.get("market"), b.get("desk"), b.get("side"))
        if key in scored_keys or key in pending_keys:
            continue  # already graded (pending path takes precedence)
        scored.append({
            "desk": b["desk"], "market": b["market"], "side": b.get("side"),
            "p": round(float(win_p), 4), "outcome": outcome,
            "brier": round((float(win_p) - outcome) ** 2, 4),
            "sen": b.get("sen"),
            "resolved_cdt": entry.get("resolved_cdt"),
            "scored_cdt": now_cdt(),
            "provenance": ("ledger-backfilled" if b.get("win_p_star")
                           else "ledger"),
            "note": b.get("receipt_id"),
        })
        scored_keys.add(key)
        n_direct += 1

    if (n_pending or n_direct) and not read_only:
        shadow["pending"] = still_pending
        shadow["scored"] = scored
        with open(SHADOW, "w") as f:
            json.dump(shadow, f, indent=2)
    return n_pending, n_direct, len(still_pending), len(scored)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--read-only", action="store_true")
    a = ap.parse_args()
    n_pending, n_direct, n_still, n_scored = resolve(read_only=a.read_only)
    if a.json:
        print(json.dumps(load_json(SHADOW, {}), indent=2))
        return
    print(f"brier: scored {n_pending + n_direct} (pending-path {n_pending}, "
          f"ledger-direct {n_direct}), still pending {n_still}, "
          f"total graded {n_scored}")


if __name__ == "__main__":
    sys.exit(main())
