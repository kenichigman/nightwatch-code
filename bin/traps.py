#!/usr/bin/env python3
"""bin/traps.py — the pre-registered trap (bounded micro-decision path, D-004).

The hyoshi answer: Nightwatch is blind between the hourly loops, and the 90s
hook must never exercise discretion or bypass the EV fortress. So the hourly
brain does the reading and pre-registers an algorithmic trap; the hook is only
the tripwire.

Two append-only logs with separated concerns:
 hidden_files/book_ledger.jsonl = RISK TAKEN (written only by book_trade.py)
 hidden_files/traps.jsonl = INTENT ARMED (armed/cancelled by the loop,
 triggered/expired by the hook)

The hook NEVER writes to the ledger. On a trigger it invokes book_trade.py,
which re-enforces every gate (kill switch, mikiri, caps, correlation,
driver, dust) with fresh state at the observed execution price. Pre-approval
is authorization to *attempt*, never a bypass — and the trap carries no size,
so D-001's "sizing computed, never chosen" survives the 59-minute fuse.

Subcommands:
 arm --desk D --market KEY --slug S --venue com|us --side yes|no
 --trigger below|above --trigger-px-c C --current-px-c NOW --p P
 --family F --driver DR --loser L --sen SE --arming-margin-pts M
 --armed-by CYCLE [--min-volume-24h N] [--note T]
 Appends an `armed` event after validation:
 - trigger beyond current price in the trigger direction
 (below: trigger < current; above: trigger > current)
 - arming margin in (0, 5): positive edge that has NOT crossed
 the band — a setup that already clears is booked directly,
 never trapped
 - <= TRAP_MAX_ARMED armed traps total, <= 1 per market
 - market key on WATCHLIST.json; desk/sen/loser validated the
 same way book_trade.py validates them (a trap cannot arm an
 invalid thesis)
 Expiry = armed + TRAP_FUSE_MIN minutes (59).
 cancel --trap-id ID --reason R --by WHO (loop kills a stale thesis)
 armed print the currently armed set as JSON (derived by replay)
 check --prices PATH (PATH: JSON {watchlist_key: {px, prev_px}},
 px in 0-1 fractions as the hook reports them)
 Replays the log, appends `expired` for past-expiry traps,
 evaluates crossings, appends `triggered` BEFORE printing the
 execution directive (crash-safe one-shot: a dead hook can never
 double-fire). Prints one JSON directive per line:
 {trap_id, desk, market, slug, venue, side, price_c, p, loser,
 sen, driver, family, note}
 price_c = observed trigger price in cents (adverse-touch
 convention — the script re-gates at this price).
 settle --trap-id ID --result accept|reject|kill --detail T
 [--receipt R]
 Appends `trap_settled` with the script's verdict.

One-shot semantics: a trap executes at most once. After `triggered` it is
consumed — ACCEPT, REJECT, or kill exit 4 all end it. The hook never re-arms;
only the next hourly loop may arm a fresh trap.

v1 trigger language is price-crossing only. min_volume_24h is reserved:
the hook's data plane carries no volume yet (state is {px, in_band}), so a
trap armed WITH a volume requirement is UNEVALUABLE — check refuses to
evaluate it (stays armed until expiry) rather than silently degrading to
price-only. Fail closed.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CDT = ZoneInfo("America/Chicago")
# HOME-relative (not script-relative): tests sandbox HOME via run_tests.sh,
# and per-test via testutil.isolated_home. A script-location ROOT would
# let a test touch the real traps.jsonl — a spec violation.
ROOT = os.path.expanduser("~/workspace/goals/10-polymarket-experiment")
TRAPS = os.path.join(ROOT, "hidden_files", "traps.jsonl")
WATCHLIST_PATH = os.path.join(ROOT, "desks", "WATCHLIST.json")

TRAP_FUSE_MIN = 59          # armed intent dies at the next hourly loop
TRAP_MAX_ARMED = 5          # at most 5 tripwires live at once (D-002 spirit)
TRAP_MAX_PER_MARKET = 1     # one trap per market — no stacked tripwires
MIKIRI_BAND_PTS = 5.0       # arming margin must sit BELOW this (not crossed)

sys.path.insert(0, ROOT)
try:
    import book_trade  # noqa: E402 (DESKS, SEN_CHOICES, MIKIRI_MIN_LOSER_LEN)
except ImportError:
    # Sandboxed tests: state lives under the sandbox HOME, but the code
    # under test is the real repo — import constants from the script's own
    # location. Code is code; state is state.
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import book_trade  # noqa: E402


def now_cdt():
    return datetime.now(CDT)


def load_events():
    evs = []
    if os.path.isfile(TRAPS):
        with open(TRAPS) as f:
            for line in f:
                line = line.strip()
                if line:
                    evs.append(json.loads(line))
    return evs


def append_event(ev):
    os.makedirs(os.path.dirname(TRAPS), exist_ok=True)
    with open(TRAPS, "a") as f:
        f.write(json.dumps(ev) + "\n")


def armed_set(events=None):
    """Derived state: armed traps = armed minus (triggered|expired|cancelled).

 Never stored as primary state — always replayed. A trap that fired is
 consumed even if the booking that followed was REJECTed: one-shot.
 """
    events = load_events() if events is None else events
    armed = {}
    for ev in events:
        t = ev.get("event")
        tid = ev.get("trap_id")
        if t == "armed":
            armed[tid] = ev
        elif t in ("triggered", "expired", "cancelled"):
            armed.pop(tid, None)
    return armed


def next_trap_id(events):
    n = sum(1 for e in events if e.get("event") == "armed") + 1
    ts = now_cdt().strftime("%Y%m%d-%H%M%S")
    return f"trap-{ts}-{n:02d}"


def load_watchlist_keys():
    try:
        with open(WATCHLIST_PATH) as f:
            wl = json.load(f)
        return set((wl.get("markets") or {}).keys())
    except (OSError, json.JSONDecodeError):
        return None


def fail(msg):
    print(f"TRAP-REJECT: {msg}", file=sys.stderr)
    return 3


def cmd_arm(a):
    events = load_events()
    live = armed_set(events)

    # --- thesis validation mirrors book_trade.py: a trap cannot arm an
    # --- invalid thesis (unreadable opponent, untagged initiative, bad p).
    if a.desk not in book_trade.DESKS:
        return fail(f"--desk must be one of {sorted(book_trade.DESKS)}")
    if not (0 < a.trigger_px_c < 100) or not (0 < a.current_px_c < 100):
        return fail("trigger/current price must be 0-100 (exclusive) cents")
    if not (0 < a.p < 1):
        return fail("p must be 0-1 (exclusive)")
    if len((a.loser or "").strip()) < book_trade.MIKIRI_MIN_LOSER_LEN:
        return fail("mikiri: --loser is required — name the source of the "
                    "mispricing. An unreadable opponent cannot be trapped.")
    if (a.sen or "").strip() not in book_trade.SEN_CHOICES:
        return fail("mikiri: --sen must be one of "
                    f"{', '.join(book_trade.SEN_CHOICES)}")
    if a.side not in ("yes", "no"):
        return fail("--side must be yes|no")
    if a.trigger not in ("below", "above"):
        return fail("--trigger must be below|above")

    # --- trigger direction: the market must travel TO the tripwire.
    if a.trigger == "below" and not (a.trigger_px_c < a.current_px_c):
        return fail(f"trigger below requires trigger_px_c "
                    f"({a.trigger_px_c}) < current ({a.current_px_c}) — "
                    f"the market must come down to the gate, not start past it")
    if a.trigger == "above" and not (a.trigger_px_c > a.current_px_c):
        return fail(f"trigger above requires trigger_px_c "
                    f"({a.trigger_px_c}) > current ({a.current_px_c})")

    # --- the "hasn't quite crossed" bound: positive edge, short of the band.
    # --- A setup already clearing the band is booked directly, never trapped.
    m = a.arming_margin_pts
    if not (0 < m < MIKIRI_BAND_PTS):
        return fail(f"arming margin {m}pts must be in (0, {MIKIRI_BAND_PTS}) — "
                    f"traps arm for near-misses, not clears (book those) "
                    f"and not negative-edge lottery tickets")

    # --- proliferation bounds (D-002 spirit: fewer, deeper).
    if len(live) >= TRAP_MAX_ARMED:
        return fail(f"{len(live)} traps already armed (max {TRAP_MAX_ARMED})")
    if any(e.get("market") == a.market for e in live.values()):
        return fail(f"market {a.market} already has an armed trap "
                    f"(max {TRAP_MAX_PER_MARKET} per market)")

    wl_keys = load_watchlist_keys()
    if wl_keys is None:
        return fail(f"WATCHLIST unreadable ({WATCHLIST_PATH}) — arming halted")
    if a.market not in wl_keys:
        return fail(f"market '{a.market}' not on WATCHLIST — traps arm only "
                    f"for watched markets")

    ts = now_cdt()
    tid = next_trap_id(events)
    ev = {"event": "armed", "trap_id": tid,
          "armed_cdt": ts.isoformat(),
          "expiry_cdt": (ts + timedelta(minutes=TRAP_FUSE_MIN)).isoformat(),
          "armed_by": a.armed_by, "desk": a.desk, "market": a.market,
          "slug": a.slug, "venue": a.venue, "side": a.side,
          "trigger": a.trigger, "trigger_px_c": a.trigger_px_c,
          "p": a.p, "family": (a.family or "").strip().lower(),
          "driver": (a.driver or "").strip().lower(),
          "loser": a.loser.strip(), "sen": a.sen.strip(),
          "arming_margin_pts": m,
          "min_volume_24h": a.min_volume_24h,
          "note": a.note or ""}
    append_event(ev)
    print(f"ARMED {tid} | {a.desk} {a.side} {a.market} "
          f"{a.trigger} {a.trigger_px_c}c (now {a.current_px_c}c) "
          f"| margin {m:+.1f}pts | expires {ev['expiry_cdt'][11:16]} CDT")
    return 0


def cmd_cancel(a):
    live = armed_set()
    if a.trap_id not in live:
        return fail(f"trap {a.trap_id} is not armed (already consumed or "
                    f"unknown) — nothing to cancel")
    append_event({"event": "cancelled", "trap_id": a.trap_id,
                  "cancelled_cdt": now_cdt().isoformat(),
                  "reason": a.reason, "by": a.by})
    print(f"CANCELLED {a.trap_id} | {a.reason}")
    return 0


def cmd_armed(_a):
    live = armed_set()
    print(json.dumps(sorted(live.values(), key=lambda e: e["trap_id"]),
                     indent=2))
    return 0


def cmd_check(a):
    """The hook's tripwire evaluation. Appends triggered/expired BEFORE
 printing directives — crash-safe one-shot."""
    try:
        with open(a.prices) as f:
            prices = json.load(f)
    except (OSError, json.JSONDecodeError) as ex:
        print(f"TRAP-ERROR: prices file unreadable ({ex}) — no evaluation, "
              f"traps stay armed", file=sys.stderr)
        return 1
    events = load_events()
    live = armed_set(events)
    now = now_cdt()
    directives = []
    for tid in sorted(live):
        ev = live[tid]
        # Expiry first: a stale trap can never execute.
        try:
            exp = datetime.fromisoformat(ev["expiry_cdt"])
        except (ValueError, TypeError):
            exp = now  # malformed expiry fails closed: treat as expired
        if now >= exp:
            append_event({"event": "expired", "trap_id": tid,
                          "expiry_cdt": ev.get("expiry_cdt"),
                          "observed_cdt": now.isoformat()})
            continue
        # v1: volume-gated traps are UNEVALUABLE until the data plane
        # carries volume. Fail closed — stay armed, never silently degrade
        # to price-only.
        if ev.get("min_volume_24h") is not None:
            continue
        px = prices.get(ev["market"]) or {}
        cur, prev = px.get("px"), px.get("prev_px")
        if cur is None or prev is None:
            continue  # no fresh read — the trap waits, it never guesses
        # The hook cache carries the Yes-side price for every market;
        # trap arm semantics are side-native (trigger_px_c is the trapped
        # side's own cents), so convert before comparing. Without this, a
        # No-side trap compares Yes prices against a No threshold and can
        # never trigger (first live trap expired untriggerable).
        if ev.get("side") == "no":
            cur, prev = 1 - cur, 1 - prev
        thr = ev["trigger_px_c"] / 100.0
        crossed = (prev > thr >= cur) if ev["trigger"] == "below" \
            else (prev < thr <= cur)
        if not crossed:
            continue
        # One-shot claim BEFORE execution: a dead hook cannot double-fire,
        # and even if it did, the correlation gate would REJECT the duplicate.
        obs_c = round(cur * 100, 2)
        append_event({"event": "triggered", "trap_id": tid,
                      "trigger_cdt": now.isoformat(),
                      "observed_px_c": obs_c,
                      "trigger_px_c": ev["trigger_px_c"]})
        directives.append({
            "trap_id": tid, "desk": ev["desk"], "market": ev["market"],
            "slug": ev["slug"], "venue": ev["venue"], "side": ev["side"],
            "price_c": obs_c, "p": ev["p"], "loser": ev["loser"],
            "sen": ev["sen"], "driver": ev["driver"],
            "family": ev["family"],
            "note": f"trap {tid} triggered @ {obs_c}c"
                    + (f" | {ev['note']}" if ev.get("note") else "")})
    for d in directives:
        print(json.dumps(d))
    return 0


def cmd_settle(a):
    if a.result not in ("accept", "reject", "kill"):
        return fail("--result must be accept|reject|kill")
    append_event({"event": "trap_settled", "trap_id": a.trap_id,
                  "settle_cdt": now_cdt().isoformat(),
                  "result": a.result, "receipt_id": a.receipt or "",
                  "detail": a.detail or ""})
    print(f"SETTLED {a.trap_id} | {a.result}"
          + (f" | {a.receipt}" if a.receipt else "")
          + (f" | {a.detail}" if a.detail else ""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="traps.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("arm")
    a.add_argument("--desk", required=True)
    a.add_argument("--market", required=True,
                   help="WATCHLIST key (hook polls by key)")
    a.add_argument("--slug", required=True)
    a.add_argument("--venue", choices=["com", "us"], required=True)
    a.add_argument("--side", choices=["yes", "no"], required=True)
    a.add_argument("--trigger", choices=["below", "above"], required=True)
    a.add_argument("--trigger-px-c", type=float, required=True)
    a.add_argument("--current-px-c", type=float, required=True)
    a.add_argument("--p", type=float, required=True)
    a.add_argument("--family", required=True)
    a.add_argument("--driver", required=True)
    a.add_argument("--loser", required=True)
    a.add_argument("--sen", required=True)
    a.add_argument("--arming-margin-pts", type=float, required=True)
    a.add_argument("--armed-by", required=True, help="arming cycle_id")
    a.add_argument("--min-volume-24h", type=float, default=None,
                   help="RESERVED v1: armed but unevaluable until the hook "
                        "carries volume")
    a.add_argument("--note", default="")

    c = sub.add_parser("cancel")
    c.add_argument("--trap-id", required=True)
    c.add_argument("--reason", required=True)
    c.add_argument("--by", required=True)

    sub.add_parser("armed")

    k = sub.add_parser("check")
    k.add_argument("--prices", required=True,
                   help="JSON file {watchlist_key: {px, prev_px}}")

    s = sub.add_parser("settle")
    s.add_argument("--trap-id", required=True)
    s.add_argument("--result", choices=["accept", "reject", "kill"],
                   required=True)
    s.add_argument("--detail", default="")
    s.add_argument("--receipt", default="")

    args = ap.parse_args(argv)
    return {"arm": cmd_arm, "cancel": cmd_cancel, "armed": cmd_armed,
            "check": cmd_check, "settle": cmd_settle}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
