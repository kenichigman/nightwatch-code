#!/usr/bin/env python3
"""build_deltas.py — closed-loop delta records for Nightwatch (Gabe's directive 2026-09-26 ~02:53 CDT).

The disconfirmation diet, as data: one DeltaRecord per scored prediction —
thesis (verbatim, never re-derived from news), p_side, outcome, realized
P&L, edge at entry, mechanical-exit flag, and the pre-registered
kill-criterion IDs evaluated for its desk. structural_failure is ALWAYS null
from this builder; it is filled by review (07:11 delta step or K3N1), never
by construction.

Mapping onto the REAL architecture (the directive named fictional files):
  - Scored predictions = PAPER.md ## Ledger rows x hidden_files/settled.json
    (the same join brier.py grades — book rows carry p_side directly).
  - Enrichment from hidden_files/book_ledger.jsonl receipts: edge_pts at
    entry, exit receipts (mechanical-exit flag + exit-computed P&L), settle
    receipts (realized P&L). Receipt notes are preferred for thesis_verbatim
    when the receipt is a real booking; bootstrap stubs fall back to the
    PAPER.md thesis cell (verbatim).
  - brier_shadow.json scored rows cover exit-graded predictions with no
    ledger row (ledger takes precedence on (desk, market) collision —
    brier.py's rule).
  - hidden_files/rejections.jsonl rows since the timestamp ride along as
    rejected candidates (not scored predictions — they have no outcome).

READ-ONLY on real state: reads the files above + LESSONS.md. Writes ONLY to
stdout (or --out). Never invents: unknowable P&L stays null, undated records
are included rather than silently dropped.

Usage:
  python3 bin/build_deltas.py [--since SINCE] [--out PATH] [--root DIR]
  --since: YYYY-MM-DD (day-granular, conservative) or a CDT timestamp
    'YYYY-MM-DD HH:MM[:SS]' / ISO with offset for finer cuts. Default: the
    last "## YYYY-MM-DD -- delta review" header in LESSONS.md (all records
    when no review exists yet).
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, date
from zoneinfo import ZoneInfo

CDT = ZoneInfo("America/Chicago")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CRITERION_IDS = [
    "CAL-WATCH",          # SPEC.md: eff_n >= 10 -> visibility
    "CAL-RECALIBRATE",    # SPEC.md: eff_n >= 15, |decayed - lifetime| >= 0.05
    "CAL-ESCALATE",       # SPEC.md: eff_n >= 15, decayed > 0.25
    "D-001-K1",           # DOCTRINES.md: MANUAL, overconfidence + propose-recalibrate
    "K1-SIZING-OVERRIDE",  # SPEC.md: PRE-REGISTERED NOT ACTIVE; |mean p - winrate| >= 5pts @ eff_n >= 10
    "R-PRECISION",        # desks/R.md: kill precision < 50% on 10+ graded kills
]


def now_cdt():
    return datetime.now(CDT)


def load_jsonl(path):
    if not os.path.isfile(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def parse_dt(raw):
    """Best-effort -> aware CDT datetime or None. Never raises."""
    if not raw:
        return None
    s = str(raw).strip().replace(" CDT", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=CDT)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=CDT)
    except ValueError:
        return None


def parse_date(raw):
    """Best-effort -> date or None. Never raises."""
    dt = parse_dt(raw)
    return dt.date() if dt else None


def parse_since(s):
    """--since: 'YYYY-MM-DD' (day-granular — conservative, matches the
    day-precision of LESSONS.md delta-review headers) or a full timestamp
    ('YYYY-MM-DD HH:MM[:SS]' in CDT, or ISO with offset) for finer cuts.
    Returns ('date', date) or ('ts', aware datetime)."""
    s = str(s).strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return ("date", date(*map(int, m.groups())))
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M"):
        try:
            return ("ts", datetime.strptime(s.replace(" CDT", ""), fmt)
                    .replace(tzinfo=CDT))
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CDT)
        return ("ts", dt.astimezone(CDT))
    except ValueError:
        raise SystemExit(
            f"bad --since (want YYYY-MM-DD or a CDT timestamp): {s!r}")


def since_excludes(since, rec_dt):
    """True when the record predates the watermark. Day-granularity input
    excludes the whole day (conservative); timestamp input is strict."""
    if since is None or rec_dt is None:
        return False
    kind, val = since
    if kind == "date":
        return rec_dt.date() <= val
    return rec_dt.astimezone(CDT) <= val


def last_delta_review(lessons_path):
    """Most recent '## YYYY-MM-DD -- delta review' header date, or None."""
    try:
        with open(lessons_path) as f:
            text = f.read()
    except OSError:
        return None
    hits = re.findall(r"^## (\d{4}-\d{2}-\d{2}) [-\u2014] delta review", text,
                      re.MULTILINE)
    if not hits:
        return None
    return max(hits)


def norm_slug(raw):
    """Strip venue suffixes like ' (.com)' — mirrors brier.py."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", str(raw).strip())


def parse_paper_ledger(root):
    """Parse PAPER.md ## Ledger (same table brier.py grades). Returns rows:
    {desk, market (norm_slug'd), side, p_side|None, thesis, ev_gate,
     pnl|None, exit_cell}."""
    path = os.path.join(root, "PAPER.md")
    rows = []
    try:
        with open(path) as f:
            lines = f.readlines()
    except OSError:
        return rows
    in_ledger, in_table = False, False
    for line in lines:
        s = line.rstrip("\n")
        if s.startswith("## Ledger"):
            in_ledger = True
            continue
        if in_ledger and s.startswith("## ") and not s.startswith("## Ledger"):
            break
        if not in_ledger:
            continue
        if s.startswith("| Date (CDT)"):
            in_table = True
            continue
        if not (in_table and s.startswith("|") and not s.startswith("|---")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 12:
            continue
        p = parse_p(cells[5])
        rows.append({
            "desk": cells[1].strip().upper(), "market": norm_slug(cells[2]),
            "side": cells[3].strip().lower(), "p_side": p,
            "thesis": cells[7], "ev_gate": cells[8].strip().lower(),
            "pnl": parse_pnl(cells[10]), "exit_cell": cells[9],
        })
    return rows


def parse_p(raw):
    s = str(raw).strip().rstrip("*")
    if not s or s in ("—", "-", "–", "n/a", "NA"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if 0.0 <= v <= 1.0 else None


def parse_pnl(raw):
    """PAPER.md P&L cell ('−1.00', '+2.50', '—') -> float|None. Never raises."""
    s = str(raw).strip().replace("−", "-").replace("+", "")
    if not s or s in ("—", "-", "–"):
        return None
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def p_side_of(receipt):
    p_yes = receipt.get("p_yes")
    if p_yes is None:
        return None
    return p_yes if receipt.get("side") == "yes" else 1.0 - p_yes


def exit_pnl(book, exit_rec):
    """Realized P&L of a pre-resolution exit, same math as book_trade exit."""
    # Prefer the receipt's own realized P&L (book_trade records it since the
    # 2026-09-26 terminal-closure change); fall back to recomputation.
    if exit_rec.get("realized_pnl_usd") is not None:
        return round(exit_rec["realized_pnl_usd"], 2)
    entry = book["price_c"]
    shares = book["size_usd"] / (entry / 100.0)
    ex = exit_rec["exit_price_c"]
    # Side-agnostic: the ledger prices the purchased token, so P&L is
    # (exit - entry) regardless of side (2026-09-26 sign fix — the old
    # No-branch flipped the sign and printed profits on losses).
    move = ex - entry
    return round(move / 100.0 * shares, 2)


def build(root, since):
    ledger = load_jsonl(os.path.join(root, "hidden_files", "book_ledger.jsonl"))
    settled = (load_json(os.path.join(root, "hidden_files", "settled.json"), {})
               .get("settled") or {})
    shadow = load_json(os.path.join(root, "hidden_files", "brier_shadow.json"),
                       {"pending": [], "scored": []})
    rejections = load_jsonl(os.path.join(root, "hidden_files",
                                        "rejections.jsonl"))
    paper = parse_paper_ledger(root)

    books = [e for e in ledger if e.get("action") == "book"]
    exits = {e["receipt_id"]: e for e in ledger if e.get("action") == "exit"}
    settles = {e["receipt_id"]: e for e in ledger
               if e.get("action") == "settle"}

    def find_receipt(desk, market):
        for b in books:
            if b.get("desk") != desk:
                continue
            if b.get("market") == market or norm_slug(b.get("market", "")) == market:
                return b
        return None

    records = []
    seen_keys = set()  # (desk, market) — ledger/paper takes precedence over shadow

    # Primary join: PAPER.md ## Ledger rows (p_side, thesis) x settled.json
    # (outcome) — the same join brier.py grades. Receipts enrich.
    for row in paper:
        if row["desk"] == "X":
            continue  # unscored sandbox — never votes on the math
        if row["ev_gate"] == "directive":
            continue  # no p by design
        if row["p_side"] is None:
            continue
        market = row["market"]
        entry = settled.get(market)
        if not entry or "yes_won" not in entry:
            continue  # unresolved — not a scored prediction yet
        outcome = 1 if (row["side"] == "yes") == bool(entry["yes_won"]) else 0
        b = find_receipt(row["desk"], market)
        ex = exits.get(b["receipt_id"]) if b else None
        st = settles.get(b["receipt_id"]) if b else None
        if st and st.get("realized_pnl_usd") is not None:
            pnl, method = round(st["realized_pnl_usd"], 2), "settle-receipt"
        elif ex and b:
            pnl, method = exit_pnl(b, ex), "exit-computed"
        elif row["pnl"] is not None:
            pnl, method = row["pnl"], "paper-pnl"
        else:
            pnl, method = None, "unknown"
        rec_dt = (parse_dt(entry.get("resolved_cdt"))
                  or parse_dt((st or {}).get("ts_cdt"))
                  or parse_dt((b or {}).get("ts_cdt")))
        if since_excludes(since, rec_dt):
            continue
        note = (b or {}).get("note") or ""
        real_booking = bool(b and b.get("p_yes") is not None
                            and not note.startswith("bootstrapped from"))
        records.append({
            "record_id": f"{b['receipt_id']}@{market}" if b
                         else f"paper-{row['desk']}-{market}",
            "market": market, "desk": row["desk"], "side": row["side"],
            "p_side": round(row["p_side"], 4), "outcome": outcome,
            "brier": round((row["p_side"] - outcome) ** 2, 4),
            "realized_pnl_usd": pnl, "pnl_method": method,
            "edge_pts_at_entry": (b or {}).get("edge_pts"),
            "mechanical_exit": bool(ex and "mechanical" in
                                    str(ex.get("note", "")).lower()),
            "thesis_verbatim": note if real_booking else row["thesis"],
            "kill_criterion_ids_evaluated": list(CRITERION_IDS),
            "structural_failure": None,
            "provenance": "booked",
            "built_cdt": now_cdt().strftime("%Y-%m-%d %H:%M CDT"),
        })
        seen_keys.add((row["desk"], market))

    # Paper-ledger theses for the Quote Gate: shadow-scored rows carry only the
    # brier_shadow note (sometimes a bootstrap placeholder); when the market
    # has a real ledger/paper thesis, quote that verbatim instead.
    paper_thesis = {row["market"]: row["thesis"] for row in paper
                    if row.get("thesis")}
    for e in shadow.get("scored", []):
        key = (e.get("desk"), e.get("market"))
        if key in seen_keys:
            continue  # ledger-scored markets take precedence (brier.py rule)
        p = e.get("p")
        outcome = e.get("outcome")
        side = str(e.get("side", "")).lower()
        if p is None or outcome is None or side not in ("yes", "no"):
            continue
        # brier.py writes resolved_cdt on scored rows (pending shadows resolved
        # at resolution carry exit_time + a "mechanical exit" note; ledger-direct
        # in-position resolutions carry provenance "ledger" and resolved_cdt).
        rec_dt = (parse_dt(e.get("resolved_cdt"))
                  or parse_dt(e.get("resolved_at"))
                  or parse_dt(e.get("settle_time")))
        if since_excludes(since, rec_dt):
            continue
        entry_prov = e.get("provenance") or "shadow"
        note = str(e.get("note") or "")
        records.append({
            "record_id": f"{entry_prov}-{e.get('desk')}-{e.get('market')}",
            "market": e.get("market"), "desk": e.get("desk"),
            "side": side,
            "p_side": round(p, 4), "outcome": outcome,
            "brier": round((p - outcome) ** 2, 4),
            "realized_pnl_usd": None, "pnl_method": "unknown",
            "edge_pts_at_entry": None,
            # Not all scored-shadow rows are exits: ledger-provenance rows are
            # held-to-resolution in-position scores. Infer from exit evidence.
            "mechanical_exit": bool(e.get("exit_time")) or "mechanical" in note.lower(),
            "thesis_verbatim": paper_thesis.get(norm_slug(e.get("market", ""))) or note,
            "kill_criterion_ids_evaluated": list(CRITERION_IDS),
            "structural_failure": None,
            "provenance": entry_prov,
            "built_cdt": now_cdt().strftime("%Y-%m-%d %H:%M CDT"),
        })

    # Per-desk criterion results: batch stats + which gates are evaluable.
    # brier.py eff_n gates are evaluated by the deep loop (step 1b runs it);
    # this builder reports the batch divergence and marks eff_n-dependent
    # criteria honestly.
    by_desk = {}
    for r in records:
        by_desk.setdefault(r["desk"], []).append(r)
    criterion_results = {}
    for desk, rs in sorted(by_desk.items()):
        ps = [r["p_side"] for r in rs]
        outs = [r["outcome"] for r in rs]
        mean_p = sum(ps) / len(ps)
        winrate = sum(outs) / len(outs)
        div_pts = abs(mean_p - winrate) * 100
        criterion_results[desk] = {
            "n_batch": len(rs),
            "mean_p_side": round(mean_p, 4),
            "win_rate": round(winrate, 4),
            "divergence_pts": round(div_pts, 2),
            "results": [
                {"id": "CAL-WATCH", "fired": False,
                 "detail": "needs brier.py eff_n >= 10 (deep-loop step 1b)"},
                {"id": "CAL-RECALIBRATE", "fired": False,
                 "detail": "needs brier.py eff_n >= 15 and |decayed - lifetime| >= 0.05"},
                {"id": "CAL-ESCALATE", "fired": False,
                 "detail": "needs brier.py eff_n >= 15 and decayed > 0.25"},
                {"id": "D-001-K1", "fired": False,
                 "detail": "MANUAL only: propose-recalibrate tier + overconfidence (mean p - winrate >= +0.05)"},
                {"id": "K1-SIZING-OVERRIDE", "fired": False,
                 "detail": ("PRE-REGISTERED, NOT ACTIVE: needs brier.py eff_n >= 10; "
                             f"batch divergence {div_pts:.1f}pts on n={len(rs)} is noise, not signal")},
                {"id": "R-PRECISION", "fired": False,
                 "detail": "needs 10+ graded kills in desks/R.md kill-note table"},
            ],
        }

    rej_since = []
    for rj in rejections:
        if since_excludes(since, parse_dt(rj.get("ts_cdt"))):
            continue
        rej_since.append(rj)  # undated rejections are included, never dropped

    since_echo = (since[1].isoformat() if since and since[0] == "date"
                  else since[1].strftime("%Y-%m-%d %H:%M CDT") if since else None)
    return {
        "generated_cdt": now_cdt().strftime("%Y-%m-%d %H:%M CDT"),
        "since": since_echo,
        "delta_records": records,
        "rejections_since": rej_since,
        "criterion_results": criterion_results,
    }


def main():
    ap = argparse.ArgumentParser(description="Build closed-loop delta records (read-only)")
    ap.add_argument("--since", default=None,
                    help="YYYY-MM-DD (day-granular, conservative) or a CDT "
                         "timestamp 'YYYY-MM-DD HH:MM[:SS]' / ISO with offset; "
                         "default: last '## YYYY-MM-DD -- delta review' in LESSONS.md")
    ap.add_argument("--out", default=None, help="write JSON here; default stdout")
    ap.add_argument("--root", default=ROOT, help="goal root (tests point at a sandbox)")
    a = ap.parse_args()
    since = None
    if a.since:
        since = parse_since(a.since)
    else:
        last = last_delta_review(os.path.join(a.root, "LESSONS.md"))
        if last:
            since = ("date", datetime.strptime(last, "%Y-%m-%d").date())
    doc = build(a.root, since)
    text = json.dumps(doc, indent=1) + "\n"
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
