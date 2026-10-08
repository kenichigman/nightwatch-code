#!/usr/bin/env python3
"""Recompute PAPER.md's scoreboard from the ledger table.

Gabe directive 2026-10-02: a manual scoreboard monitoring an automated
pipeline is an architectural contradiction. This script derives the
scoreboard's numeric columns directly from the ledger rows, so the two
can never drift.

Rules (ratified by construction):
- Source of truth: the ledger table between LEDGER-TABLE-BEGIN/END.
- Per desk (M/S/F/Q/C): realized = sum of P&L cells (first number in the
  cell; Unicode minus handled), trades = total rows, wins = P&L > 0,
  win_rate = wins/trades (— when trades == 0).
- Fill-regime split (2026-10-06): the ledger table's Fill column tags each
  row v1 (0.5c haircut, no fees) or v2 (book-walk VWAP + taker fees). The two
  regimes are NOT pooled — the Realized P&L cell renders the all-time total
  with the v2-regime subtotal in parentheses, e.g. `−$8.61 (v2 −$5.20)`.
  Rows predating the Fill column count as v1. Trades/Wins/Win rate remain
  all-time counts (the Fill column on each row carries the per-trade regime
  for audit).
- Desk X is UNSCORED by charter: its row is never touched.
- Only the numeric cells (Realized P&L, Trades, Wins, Win rate) are
  rewritten. Start, Current, Open risk, and the notes column are preserved.
- Open positions (empty P&L cell) count as trades but not as realized.
- Idempotent: running twice without ledger changes produces no diff.

Usage: python3 bin/recompute_scoreboard.py [--check]
  --check: exit 0 if the scoreboard already matches, exit 2 with a diff
           description if it doesn't (for workers to detect drift).
"""
import re
import sys
from datetime import datetime

PAPER = "PAPER.md"
SCORED_DESKS = ("M", "S", "F", "Q", "C")  # X unscored by charter


def parse_pnl(cell):
    cell = cell.strip()
    if not cell or cell in ("—", "-", ""):
        return None
    m = re.search(r"[−\-]?\d[\d,]*\.?\d*", cell)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "").replace("−", "-"))
    except ValueError:
        return None


def fmt_money(v):
    s = f"${abs(v):.2f}"
    return ("−" + s) if v < -0.004 else s


def fmt_realized(st):
    # Fill-regime split (2026-10-06): the Realized P&L cell renders the
    # all-time total with the v2-bookwalk subtotal in parentheses. The split
    # is omitted when one regime is absent (pure-v1 legacy, v2 ~ 0; or
    # pure-v2, v2 ~ all-time) — the ledger table's Fill column carries the
    # per-row regime either way.
    base = fmt_money(round(st["realized"], 2))
    v2 = st["realized_v2"]
    if abs(v2) < 0.004 or abs(st["realized"] - v2) < 0.004:
        return base
    return f"{base} (v2 {fmt_money(round(v2, 2))})"


def main():
    check_only = "--check" in sys.argv
    text = open(PAPER).read()
    lines = text.split("\n")
    b = lines.index("<!-- LEDGER-TABLE-BEGIN -->")
    e = lines.index("<!-- LEDGER-TABLE-END -->")
    rows = [l for l in lines[b:e] if l.startswith("| 202")]

    stats = {}
    for desk in SCORED_DESKS:
        stats[desk] = {"realized": 0.0, "realized_v2": 0.0,
                       "trades": 0, "wins": 0}
    for r in rows:
        cells = [c.strip() for c in r.split("|")]
        book = cells[2]
        if book not in stats:
            continue
        stats[book]["trades"] += 1
        v = parse_pnl(cells[11])
        # Fill column is cells[12]; rows predating it count as v1.
        regime_v2 = len(cells) > 12 and cells[12] == "v2"
        if v is not None:
            stats[book]["realized"] += v
            if regime_v2:
                stats[book]["realized_v2"] += v
            if v > 0:
                stats[book]["wins"] += 1

    # rewrite the scoreboard rows
    out = []
    changed = []
    in_board = False
    for i, ln in enumerate(lines):
        if ln.startswith("| Book | Start |"):
            in_board = True
            out.append(ln)
            continue
        if in_board and ln.startswith("|---"):
            out.append(ln)
            continue
        if in_board and ln.startswith("| "):
            cells = [c for c in ln.split("|")]
            # cells[0]='', cells[1]=' M ', cells[2]=' $10.00 ', ...
            desk = cells[1].strip()
            if desk in stats:
                st = stats[desk]
                wr = "—" if st["trades"] == 0 else f"{round(100*st['wins']/st['trades'])}%"
                new_cells = list(cells)
                new_cells[4] = f" {fmt_realized(st)} "
                new_cells[6] = f" {st['trades']} "
                new_cells[7] = f" {st['wins']} "
                new_cells[8] = f" {wr} "
                new_ln = "|".join(new_cells)
                if new_ln != ln:
                    changed.append(desk)
                out.append(new_ln)
                continue
            # X row or unknown: untouched
            out.append(ln)
            # end of board at the first non-table line after rows started
            continue
        if in_board and not ln.startswith("|") and ln.strip():
            in_board = False
        out.append(ln)

    if check_only:
        if changed:
            print(f"DRIFT: scoreboard differs from ledger for desks: {', '.join(changed)}")
            return 2
        print("OK: scoreboard matches ledger")
        return 0

    if changed:
        open(PAPER, "w").write("\n".join(out))
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"recomputed {ts}: updated desks {', '.join(changed)}")
    else:
        print("no drift: scoreboard already matches ledger")
    return 0


if __name__ == "__main__":
    sys.exit(main())
