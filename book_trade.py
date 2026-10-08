#!/usr/bin/env python3
"""book_trade.py — the ONLY valid path for paper bookings in Nightwatch.

The operator's enforcement rule: sizing, EV, caps, and correlation
clusters are CODE, not charter prose. The worker agent never chooses a dollar
size — this script computes it from (side, price, p). A booking without a
script receipt is invalid.

Subcommands:
 book --desk M|S|F|Q|C --market SLUG --side yes|no --price CENTS --p PYES
 --family FAMILY --driver DRIVER --loser LOSER --sen SEN
 [--directive] [--note TEXT]
 [--proposer ID] [--size-suggest USD] (proposer contract: advisory only)
 p = P(Yes resolves true), 0-1 exclusive (same convention as kelly.py)
 DRIVER = macro driver from hidden_files/driver_taxonomy.json
 (required; directives declare it for tagging but are cap-exempt)
 LOSER = named source of the mispricing (required, D-003 mikiri)
 SEN = ken_no_sen | tai_no_sen | tai_tai_no_sen (required, D-003)
 shadow --market SLUG --side yes|no --price CENTS --shadow-of RECEIPT
 --attempted DOLLARS --fill DOLLARS [--note TEXT] (X only)
 exit --receipt ID --exit-price CENTS [--note TEXT]
 settle --market SLUG --outcome YES|NO [--pnl USD] [--evidence TEXT]
 [--resolved-cdt "YYYY-MM-DD HH:MM"] [--note TEXT]
 Close ALL open receipts on a resolved market (primary settlement
 path): appends a `settle` receipt per open book row, records the
 immutable settled.json entry (with `yes_won` so brier.py resolves),
 resolve-sweep [--dry-run]
 Phase 1.2 resolution detection: check every open position's market
 against the venue; auto-settle RESOLVED markets through the settle
 path above, queue AMBIGUOUS ones for human review (never
 auto-settled). Only closes exposure — ungated like settle.
 files p-bearing rows into brier_shadow.json pending, and removes the
 position from worker_state.json / WATCHLIST.json position fields.
 Re-settling a settled market is refused (immutability).
 audit reconcile ledger vs worker_state.json positions
 ledger dump open positions
 bootstrap seed ledger from current worker_state.json (one-time)
 kill engage the kill switch (--reason TEXT): book/shadow/bootstrap
 refuse with exit code 4 until `resume` clears it. `exit` stays live
 (kill = no new risk, not no writes — a kill switch must never hold
 a bad position open)
 resume clear the kill switch, re-opening the booking path

Kill switch (code-enforced; kill switch fires a stop condition — see below):
 The check lives HERE, not in coordinator prose — this script is the single
 choke point every booking passes through, so the kill inherits the same
 guarantee the sizing fix earned. When hidden_files/kill.switch exists,
 book/shadow/bootstrap hard-exit BEFORE any write (exit code 4, distinct
 from REJECT=3). `exit` is NOT blocked: kill means no NEW risk — exits only
 close positions and book mechanical stops, they cannot open exposure.
 Read-only commands (audit, ledger) still work — that is how you verify
 state after a kill. Engage/clear via the kill/resume subcommands (the flag
 file carries timestamp + reason for the audit trail).
 Note: the scheduler's own disable is between-cycles only — no
 cancel-running-run primitive exists in the cron tools, so a cycle already
 in flight runs to completion (~10-20 min). That is a permanent accepted
 limitation; this script's kill is the mid-cycle backstop.

Phase 1.1 data-health gate (ingestion backlog): the price-watch
 hook's heartbeat (~/hooks/state/nightwatch-status.json: last_tick,
 fetch_ok/fetch_fail) is wired into this SAME choke point — book/shadow/
 bootstrap hard-exit (exit 4) when the heartbeat is missing, malformed,
 older than DATA_HEALTH_TTL_S (180s = two missed 90s polls; the threshold
 maps to the physical sensor limit per the TTL amendment), or
 when a whole tick fetched nothing (transport dark). `exit` and `settle`
 stay live: the gate kills new risk, never the ability to flatten.
 resolve-sweep (Phase 1.2) only closes exposure, so it is ungated like
 settle.

Hard gates (code, not prose):
 - Mikiri EV gate (D-003, the operator's directive): the static
 p-price band is REPLACED by the confidence-bounded form
 (win_p - k*sigma_desk) - price_c > 0.05, else REJECT. sigma_desk is the
 desk's calibration uncertainty from resolved history
 (brier_shadow.json scored rows, 21d half-life decay). A thesis from a
 poorly calibrated desk gets its margin compressed by the k*sigma penalty
 and fails where the static gate would have passed. Kelly still sizes the
 STATED win_p once the gate clears — the gate does the refusing (mikiri
 is selection), Kelly does the sizing. Cold start: a desk with
 eff_n < MIKIRI_MIN_EFF_N has no resolved history (unreadable) — the
 static gate applies but the receipt is tagged mikiri_exempt, and the
 exemption dies permanently once eff_n reaches the threshold. Skipped for
 --directive (the operator's direct orders are not EV-gated).
 - Size BY CONSTRUCTION: quarter-Kelly from (side, price, p, bankroll, cap),
 rounded DOWN to the nearest $0.05. Below $0.10 -> REJECT (dust).
 r <= 1.0 holds structurally: the agent never passes a size.
 (Deviation from F charter "nearest $0.05": nearest can breach r<=1.0;
 floor cannot. The operator's r<=1.0 rule wins.)
 - Caps: <8 open positions per desk; daily new-trade cap per desk
 (M/S/Q/C: 3, F: 5). Directives count toward the open cap, not daily-new.
 - Correlation: ONE open position per event family ACROSS ALL DESKS.
 Family = mechanical derivation from the market slug OR the declared
 --family; a match on either blocks. X shadows exempt (they mirror).
 - Driver concentration: max 2 open positions per macro driver ACROSS ALL
 DESKS (M/S/F/Q/C). --driver is REQUIRED on every booking and must be a
 key in hidden_files/driver_taxonomy.json (framework-owned vocabulary);
 missing/unknown driver REJECTs. The cap is ABSOLUTE:
 directives declare --driver for tagging but are NOT exempt — a directive
 on a full driver is rejected like any other booking. X shadows exempt
 (they mirror by design). Grandfathered:
 the 3 iran-geopolitics positions open at gate launch (bk-bootstrap-06,
 bk-bootstrap-07, bk-bootstrap-08) are not retroactively killed; the cap
 binds NEW bookings, and their backfilled driver tags count toward it —
 a 4th Iran-driver pile-on is blocked from here on.
 - Real-money nomination: --nominate-real requires --r-rating HARD|SOFT|MISS
 and is recorded. (Structural backstop unchanged: the worker never holds
 the key; no paper-book path can reach real money.)
 - Settlement immutability: a market already in settled.json cannot be
 settled again (refused, not overwritten). `settle` writes `yes_won` into
 the settled.json entry — the field brier.py's outcome_for actually
 reads — so pending shadow rows and PAPER.md ledger rows grade on the
 next brier.py run instead of silently starving.
 - Terminal closure (the operator's ruling): `exit` and `settle` mutate
 the book row itself to closed (status, close action, timestamp, final
 realized P&L) — the ledger reads absolute reality at rest; settled.json
 is no longer an exclusion filter hiding technically-open rows. Ghost
 state: if a market is already in settled.json but ledger rows remain
 open (the old filter hid them), `settle` completes the ledger-side
 closure using the recorded outcome — settled.json is never rewritten.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CDT = ZoneInfo("America/Chicago")
ROOT = os.path.expanduser("~/workspace/goals/10-polymarket-experiment")
LEDGER = os.path.join(ROOT, "hidden_files", "book_ledger.jsonl")
WS_PATH = os.path.join(ROOT, "hidden_files", "worker_state.json")
KILL_SWITCH = os.path.join(ROOT, "hidden_files", "kill.switch")
DOCTRINE_TRIP = os.path.join(ROOT, "hidden_files", "doctrine.trip")
HOOK_PRICES = os.path.expanduser("~/hooks/state/nightwatch-prices.json")

try:
    import stream_watch
except ImportError:  # pragma: no cover — sibling file, always present
    stream_watch = None
try:
    sys.path.insert(0, os.path.join(ROOT, "bin"))
    import provenance
except ImportError:  # pragma: no cover — deployed alongside; warn loudly
    provenance = None
try:
    import fill_engine as fe
except ImportError:  # pragma: no cover — deployed alongside; fail loudly below
    fe = None
HOOK_STATUS = os.path.expanduser("~/hooks/state/nightwatch-status.json")
# Phase 1.1: two missed 90s poll ticks = dark. One missed tick is tolerated
# (transient); the threshold maps to the sensor's physical limit, not to a
# rhetorical bound (TTL amendment).
DATA_HEALTH_TTL_S = 180
RESOLVE_REVIEW = os.path.join(ROOT, "hidden_files", "resolution_review.jsonl")
WATCHLIST_PATH = os.path.join(ROOT, "desks", "WATCHLIST.json")
REJECTIONS = os.path.join(ROOT, "hidden_files", "rejections.jsonl")
SETTLED_PATH = os.path.join(ROOT, "hidden_files", "settled.json")
DRIVER_TAXONOMY_PATH = os.path.join(ROOT, "hidden_files", "driver_taxonomy.json")
DRIVER_CAP = 2  # max open positions per macro driver across M/S/F/Q/C
# D-001 K1-bis interim regime (R HUNT #2 adjudicated): a desk that
# fires K1-bis (majority of trailing-30d bookings mikiri-exempt) is confined
# here until its eff_n reaches MIKIRI_MIN_EFF_N. Written by audit_doctrines.py
# on a new filing; enforced + self-clearing in cmd_book below.
INTERIM_PATH = os.path.join(ROOT, "hidden_files", "doctrine_interim.json")
BRIER_SHADOW = os.path.join(ROOT, "hidden_files", "brier_shadow.json")
FUNNEL_CACHE = os.path.join(ROOT, "hidden_files", "funnel_cache.json")
DECISION_FEATURES = os.path.join(ROOT, "hidden_files", "decision_features.jsonl")
WATCHLIST_PATH = os.path.join(ROOT, "desks", "WATCHLIST.json")
STATUS_PATH = os.path.join(ROOT, "desks", "STATUS.md")
# Kill semantic (operator's ruling): NO NEW RISK.
# book/shadow/bootstrap are blocked while the flag exists. `exit` is
# deliberately NOT blocked — a kill switch must never be the thing holding a
# bad position open. Exits only reduce risk (close positions, book stops);
# they cannot open new exposure. This matches exchange kill-switch convention
# (flatten, don't freeze) and avoids the blunt-instrument failure mode where
# a safety mechanism holds the bag it was meant to protect.

ERROR_BAND = 0.05
# Mikiri gate parameters (D-003, the operator's directive).
MIKIRI_K = 1.0          # z-multiplier on the calibration penalty.
                        # STARTING GUESS, NEVER TUNED — a settled parameter
                        # must be derived from evidence, not hardcoded
                        # (AGENTS.md); k ships labeled until the false-refusal
                        # audit (D-003 K2) validates it against resolutions.
MIKIRI_MIN_EFF_N = 5.0  # below this decay-weighted resolved count the desk
                        # is unreadable: cold-start regime (static gate +
                        # mikiri_exempt tag). STARTING GUESS, NEVER TUNED.
# Initiative tags (D-003 thesis schema): which of Musashi's three sen the
# thesis belongs to. ken_no_sen = originate before the market moves;
# tai_no_sen = wait, then cut the overreaction; tai_tai_no_sen = join the
# motion (X's shadow-mirror). Validated in code (not argparse choices) so a
# bad tag REJECTs through the logged path instead of dying at parse time.
SEN_CHOICES = ("ken_no_sen", "tai_no_sen", "tai_tai_no_sen")
MIKIRI_MIN_LOSER_LEN = 4  # a named loser shorter than this is evasion
                          # ("n/a", "x") — the read must be stated.
DESKS = {
    "M": {"bankroll": 10.0, "cap": 1.0, "fraction": 0.25, "max_open": 8, "max_new_day": 3},
    "S": {"bankroll": 500.0, "cap": 10.0, "fraction": 0.25, "max_open": 8, "max_new_day": 3},
    "F": {"bankroll": 10.0, "cap": 1.0, "fraction": 0.25, "max_open": 8, "max_new_day": 5},
    "Q": {"bankroll": 10.0, "cap": 1.0, "fraction": 0.25, "max_open": 8, "max_new_day": 3},
    "C": {"bankroll": 10.0, "cap": 1.0, "fraction": 0.25, "max_open": 8, "max_new_day": 3},
    # X is the exploration account (rechartered per the operator's stated
    # original intention; spend directive): originates
    # freely, no EV gate. Wider caps fit the $1M paper bankroll, the
    # exploration mandate, and the spend directive (mass data).
    "X": {"bankroll": 1000000.0, "cap": 20000.0, "fraction": 1.0,
          "max_open": 100, "max_new_day": 50},
}

# X exploration account: breadth-first target clip (the operator's
# "breadth first" decision on the reviewer's ordered plan). Small depth-capped clips
# across many markets — resolutions per week are the scarce input, and the
# $20k flat answered neither "what survives at size?" (the old haircut/cap
# didn't measure depth) nor "what works?" (a few big clips resolve slowly).
# $2,000 = 0.2% of the $1M paper bankroll; the 1c depth cap binds below it
# on thin books. Easily tunable; the tuning is a charter decision, not code.
X_TARGET_TRADE_USD = 2000.0

VENUE_PREFIXES = ("us-x-", "us-", "cpc-", "ipcc-")
MONTHS = {"january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december",
          "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct",
          "nov", "dec"}
FILLER = {"will", "the", "a", "an", "to", "by", "before", "through", "of",
          "on", "in", "is", "it", "s", "x", "continues", "returns", "normal",
          "continue", "return", "vs", "and", "or", "for", "with", "from"}


def now_cdt():
    return datetime.now(CDT)


def derive_family(slug):
    """Mechanical event-family from the market slug. The agent cannot game
 this — it comes from the slug, not from a declared tag."""
    s = slug.lower()
    for pre in VENUE_PREFIXES:
        if s.startswith(pre):
            s = s[len(pre):]
            break
    toks = re.split(r"[^a-z0-9]+", s)
    keep = []
    for t in toks:
        if not t or t in FILLER or t in MONTHS:
            continue
        if t.isdigit():  # years, days, date blobs — never event identity
            continue
        if re.fullmatch(r"[a-z]{3}\d{1,2}", t):  # sep30, oct31
            continue
        keep.append(t)
    return "-".join(sorted(set(keep))) or s


def load_ledger():
    if not os.path.isfile(LEDGER):
        return []
    out = []
    with open(LEDGER) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def ws_entry_dollars(p):
    """worker_state position entry in dollars, unit-aware.

 Legacy keys carry `entry` (dollars); worker-written keys carry
 `entry_c` (cents). Current skill-mandated list-form positions carry
 side-native `entry_yes_c`/`entry_no_c` (cents). Returns None when
 none is recorded. (: the audit fallback read only `entry`,
 so every `entry_c`-keyed position fell through to a bare desk+side
 match and manufactured AMBIGUOUS claims — e.g. bk-20260927-021
 claimed by 4 unrelated F/no keys.)"""
    e = p.get("entry")
    if e is not None:
        return e
    for k in ("entry_c", "entry_yes_c", "entry_no_c"):
        ec = p.get(k)
        if ec is not None:
            return ec / 100.0
    return None


def ws_entry_close_enough(p, price_c):
    """Legacy-fallback proximity check: True when the ws position's recorded
 entry is absent (weak match) or within 2c of the ledger price."""
    entry = ws_entry_dollars(p)
    return entry is None or abs(entry - price_c / 100.0) < 0.02


def ws_entry_side_dollars(p, side):
    """worker_state entry on the BOOKED side, in dollars, side-aware.

 The ledger's price_c is the booked side's price. List-form ws
 positions record side-native entry_yes_c/entry_no_c, so compare
 like-for-like: side No uses entry_no_c (else 1 - entry_yes_c);
 side Yes uses entry_yes_c (else 1 - entry_no_c). Falls back to the
 side-agnostic ws_entry_dollars for legacy entry/entry_c rows.
 Returns None when no entry data exists. (:
 without this, bootstrap No rows booked at 99.0c never matched their
 ws rows carrying entry_yes_c=1.5, producing false ORPHANs.)"""
    s = (side or "").lower()
    if s == "no":
        en = p.get("entry_no_c")
        if en is not None:
            return en / 100.0
        ey = p.get("entry_yes_c")
        if ey is not None:
            return 1.0 - ey / 100.0
    else:
        ey = p.get("entry_yes_c")
        if ey is not None:
            return ey / 100.0
        en = p.get("entry_no_c")
        if en is not None:
            return 1.0 - en / 100.0
    return ws_entry_dollars(p)


def ws_entry_side_close_enough(p, side, price_c):
    """Side-aware variant of ws_entry_close_enough: same 2c band, but the
 ws entry is taken on the booked side. True when no entry data exists
 (weak match), False on side-ambiguous legacy rows only via the same
 weak-match rule."""
    entry = ws_entry_side_dollars(p, side)
    return entry is None or abs(entry - price_c / 100.0) < 0.02


def load_interim_regime():
    """D-001 K1-bis interim regimes, desk -> regime record. Empty when none."""
    try:
        with open(INTERIM_PATH) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def set_interim_regime(desk, regime, reason):
    """Confine a desk to an interim regime. Idempotent: the first firing wins
 and keeps its original `since` — a re-fire must not rewrite the clock."""
    cur = load_interim_regime()
    if desk in cur:
        return False
    cur[desk] = {"regime": regime, "since_cdt": now_cdt().isoformat(),
                 "until": f"eff_n>={MIKIRI_MIN_EFF_N:g}",
                 "reason": (reason or "")[:300]}
    os.makedirs(os.path.dirname(INTERIM_PATH), exist_ok=True)
    with open(INTERIM_PATH, "w") as f:
        json.dump(cur, f, indent=2)
        f.write("\n")
    return True


def clear_interim_regime(desk, reason):
    """Lift a desk's interim regime. Loud: the lift is a regime change."""
    cur = load_interim_regime()
    if desk not in cur:
        return False
    del cur[desk]
    with open(INTERIM_PATH, "w") as f:
        json.dump(cur, f, indent=2)
        f.write("\n")
    print(f"INTERIM-LIFTED {desk} | {reason}")
    return True


def load_drivers():
    """Controlled driver vocabulary (framework-owned). Returns the key->meta dict,
 or None if the taxonomy is unreadable — the book path FAILS CLOSED in
 that case: no new risk without a verifiable driver."""
    try:
        doc = json.load(open(DRIVER_TAXONOMY_PATH))
        drivers = doc.get("drivers") or {}
        return {str(k).strip().lower(): v for k, v in drivers.items() if k}
    except Exception:
        return None


def append(entry):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry) + "\n")


def ledger_append_and_close(new_entries, closures, patches=None):
    """Atomic ledger write: append new_entries AND terminally close book rows.

 (the operator's ruling #2 — terminal closure): a book row whose risk is
 gone must read closed AT REST. closures maps receipt_id -> fields merged
 into the action==book row (plus status="closed"). The exit/settle receipts
 in new_entries remain the append-only audit trail; the row is the state.

 patches (optional) maps receipt_id -> fields merged into the book row
 WITHOUT changing its status — for reconciliation metadata (venue, size
 corrections) that must not terminally close a live row. Added 
 when the PAPER.md backfill needed exactly this distinction.

 Temp-file + os.replace keeps the write atomic — a crash cannot leave a
 half-written ledger, and re-running the closer completes the missing
 pieces idempotently (already-closed rows are simply re-closed).
 """
    patches = patches or {}
    out = []
    if os.path.isfile(LEDGER):
        with open(LEDGER) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                if e.get("action") == "book":
                    rid = e.get("receipt_id")
                    if rid in closures:
                        e.update(closures[rid])
                        e["status"] = "closed"
                    elif rid in patches:
                        e.update(patches[rid])
                out.append(json.dumps(e))
    for ne in new_entries:
        out.append(json.dumps(ne))
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, LEDGER)


def settled_markets():
    """Markets in settled.json are resolved — immutable, never re-queried."""
    try:
        s = json.load(open(SETTLED_PATH))
        return set((s.get("settled") or {}).keys())
    except Exception:
        return set()


def open_positions(entries):
    # A receipt is closed by an `exit` OR a `settle` action (the settle
    # subcommand is the primary settlement path), or by its own status field
    # reading "closed" (terminal closure, the operator's ruling #2).
    #
    # The old settled.json exclusion backstop is REMOVED by that same ruling:
    # it hid technically-open rows behind a sidecar file and manufactured
    # the ghost state the ruling kills. The ledger row's status is now the
    # SOLE authority on openness. A resolved-but-unsettled market correctly
    # reads open until `settle` terminally closes it (the ghost-completion
    # path in cmd_settle repairs pre-existing cases). New bookings on
    # resolved markets are still refused — cmd_book checks settled.json
    # directly at booking time.
    closed = {e["receipt_id"] for e in entries
              if e.get("action") in ("exit", "settle")}
    return [e for e in entries
            if e.get("action") == "book" and e.get("status") == "open"
            and e["receipt_id"] not in closed]


def next_receipt(entries):
    n = sum(1 for e in entries if e.get("action") == "book") + 1
    return f"bk-{now_cdt():%Y%m%d}-{n:03d}"


def desk_calibration(desk):
    """Return (eff_n, sigma_fn) for the mikiri gate.

 Reads scored (p, outcome) rows from brier_shadow.json — the designed
 calibration store (SPEC.md calibration policy). eff_n is the 21-day
 half-life decay-weighted resolved count. sigma_fn(p) returns
 sqrt(p*(1-p)/eff_n): the binomial standard error of the desk's track
 record at the thesis p — how much the desk's p-estimates can be trusted.

 Returns (eff_n, None) when eff_n < MIKIRI_MIN_EFF_N: the desk is
 unreadable and the gate fails closed (cold-start exemption aside).
 Scored rows without a resolved timestamp weight 1.0 (documented
 fallback — the store should carry resolved_cdt; see bin/brier.py).
 """
    doc = load_json_doc(BRIER_SHADOW, {"pending": [], "scored": []})
    now = now_cdt()
    eff_n = 0.0
    for s in doc.get("scored", []) or []:
        if s.get("desk") != desk:
            continue
        ts = (s.get("resolved_cdt") or s.get("scored_cdt") or "")[:16]
        w = 1.0
        if ts:
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M").replace(tzinfo=CDT)
                age_days = (now - dt).total_seconds() / 86400.0
                if age_days >= 0:
                    w = 0.5 ** (age_days / 21.0)
            except ValueError:
                w = 1.0
        eff_n += w
    if eff_n < MIKIRI_MIN_EFF_N:
        return eff_n, None

    def sigma(p):
        return ((p * (1.0 - p)) / eff_n) ** 0.5

    return eff_n, sigma


def kelly_size(side, price_c, p_yes, bankroll, cap, fraction, sigma=None):
    """Returns (size_usd, margin_pts, win_p) or (None, margin_pts, win_p) on gate fail.

 Mikiri gate (D-003): the refusal bar is the confidence-bounded margin
 (win_p - k*sigma) - price_c > ERROR_BAND. sigma=None means the desk is
 unreadable (cold start) — the caller applies the static gate and tags the
 receipt mikiri_exempt. Kelly sizes the STATED win_p: the gate refuses,
 sizing sizes. margin_pts is reported in points for the rejection log.
 """
    c = price_c / 100.0
    win_p = p_yes if side == "yes" else 1.0 - p_yes
    penalty = MIKIRI_K * sigma if sigma else 0.0
    margin = (win_p - penalty) - c
    if margin <= ERROR_BAND:
        return None, margin * 100, win_p
    f_star = (win_p - c) / (1 - c)
    if f_star <= 0:
        return None, margin * 100, win_p
    size = f_star * fraction * bankroll
    if cap is not None and size > cap:
        size = cap
    # Floor to nickel in EXACT integer cents: r<=1.0 by construction, and the
    # floored size never exceeds the raw Kelly size. (: the old
    # `int(size // 0.05)` floored $1.00 to $0.95 — 1.0 // 0.05 is 19.0 in
    # binary floating point. repair #2: the interim
    # `int(round(size * 100))` could round UP half a cent before the nickel
    # floor — raw $1.046 became $1.05 (above raw) and raw $0.096 became $0.10
    # (sneaking past the $0.10 dust line). The +1e-6 guards binary
    # representation ($1.00 stored as 99.9999999c) without ever rounding up:
    # float64 error on size*100 is < 1e-9c, six orders below the epsilon,
    # which is six orders below half a cent.)
    size = (int(size * 100 + 1e-6) // 5) * 5 / 100
    if size < 0.10:
        return None, margin * 100, win_p  # dust: edge too thin to express
    return round(size, 2), margin * 100, win_p


def kill_engaged():
    """Return the kill flag's content (timestamp + reason) if engaged, else None."""
    try:
        with open(KILL_SWITCH) as f:
            return f.read().strip() or "(no reason recorded)"
    except FileNotFoundError:
        return None


PROVENANCE_BLOCK_LOG = os.path.join(ROOT, "hidden_files",
                                    "provenance_blocks.jsonl")


def _log_provenance_block(cmd, str_fields):
    """Append an audit row for a refused local-provenance booking attempt."""
    tag = provenance.extract_text_tag(" ".join(str_fields))
    row = {
        "ts": datetime.now(CDT).isoformat(timespec="seconds"),
        "cmd": cmd,
        "tag": tag,
        "fields_sha256": hashlib.sha256(
            "\x00".join(str_fields).encode("utf-8")).hexdigest()[:32],
    }
    try:
        os.makedirs(os.path.dirname(PROVENANCE_BLOCK_LOG), exist_ok=True)
        with open(PROVENANCE_BLOCK_LOG, "a") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass  # logging must never break the refusal itself


def doctrine_tripped():
    """Return tripped proposal ids if a doctrine trip is active, else None.

 Written ONLY by bin/trip_doctrines.py on kill-class proposals for the
 risk-path doctrines (D-001/D-003/D-004). Cleared ONLY by the framework or the operator
 after adjudication — cmd_resume deliberately does NOT touch this file
 (the worker must never clear its own trip).
 """
    try:
        with open(DOCTRINE_TRIP) as f:
            ids = [line.split()[0] for line in f if line.strip()]
    except FileNotFoundError:
        return None
    return ",".join(ids) if ids else None


def data_health():
    """Phase 1.1: wire the price-watch hook's heartbeat into the booking halt.

 Returns None when the data plane is healthy, else a reason string.
 Fail-closed: a missing, malformed, future-dated, or stale heartbeat, or
 a tick in which every fetch failed (transport dark), halts NEW risk.
 Checked only on the book/shadow/bootstrap path in main — `exit` and
 `settle` stay live by design (flatten, don't freeze).
 """
    try:
        with open(HOOK_STATUS) as f:
            st = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return "data_health:heartbeat_missing"
    try:
        last = datetime.strptime(st["last_tick"], "%Y-%m-%dT%H:%M:%SZ")
        last = last.replace(tzinfo=timezone.utc)
    except (KeyError, ValueError, TypeError):
        return "data_health:heartbeat_malformed"
    age = (datetime.now(timezone.utc) - last).total_seconds()
    if age < 0:
        return "data_health:heartbeat_from_future"
    if age > DATA_HEALTH_TTL_S:
        return f"data_health:stale_heartbeat:{int(age)}s"
    ok = st.get("fetch_ok", 0)
    ff = st.get("fetch_fail", 0)
    if ok == 0 and (ok + ff) > 0:
        return "data_health:transport_dark"
    return None
    return ",".join(ids) if ids else None


def cmd_kill(a):
    reason = a.reason or "(no reason recorded)"
    stamp = datetime.now(CDT).strftime("%Y-%m-%d %H:%M %Z")
    with open(KILL_SWITCH, "w") as f:
        f.write(f"{stamp} | {reason}\n")
    print(f"KILL SWITCH ENGAGED @ {stamp} — all writes blocked. Reason: {reason}")
    return 0


def cmd_resume(_a):
    try:
        os.remove(KILL_SWITCH)
    except FileNotFoundError:
        print("kill switch was not engaged; nothing to clear")
        return 0
    stamp = datetime.now(CDT).strftime("%Y-%m-%d %H:%M %Z")
    print(f"KILL SWITCH CLEARED @ {stamp} — booking path re-opened")
    return 0


# Cents/dollars ambiguity is impossible by construction (the operator's
# directive; hardened repair #2): every price entering the booking
# math passes through parse_price_cents (the single choke point — the unit
# is decided here, not in prose), and check_price_units cross-checks the
# unit against the poller quote at booking time. The construction:
# - direct match (2c tolerance for quote staleness) -> unambiguous cents
# - 100x-low whose x100 matches the quote -> the dollars-passing error,
# rejected ALWAYS (the smoking gun; no override — if you truly want a
# limit 100x below quote, that path does not exist yet)
# - BOTH readings match (low-price markets: 0.05 against a 5c quote reads
# as 0.05c or $0.05) -> genuinely ambiguous, rejected unless the
# operator explicitly asserts cents with --confirm-cents
# - NO poller quote (off-watchlist / dark feed) -> units unverifiable,
# rejected unless --confirm-cents. New risk is never booked blind.
# (Exits keep fail-open on a dark feed — loss-capping must never be
# blocked; see cmd_exit.)
# - neither reading matches -> a limit price away from quote, passes
# Fractional cents (87.5) and sub-cent prices (0.8) are legitimate and pass
# — the tripwire only fires on the confusion/ambiguity patterns, so real
# longshot prices are never flagged.
UNIT_DIRECT_TOL_C = 2.0      # cents; quote-staleness allowance, at-quote only
UNIT_CONFUSION_TOL_C = 10.0  # cents; the 100x error is unmistakable inside this


def parse_price_cents(raw, field="--price"):
    """The ONLY valid entry point for a price into the booking math.

 The CLI contract is cents; this converts raw input to the float-cents
 the ledger stores. Anything outside (0, 100) is refused here with the
 unit named — never silently interpreted.
 """
    try:
        p = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{field}: price must be a number in CENTS "
                         f"(got {raw!r})")
    if not (0 < p < 100):
        raise ValueError(f"{field}: price must be in CENTS, 0 < c < 100 "
                         f"(got {raw!r})")
    return p


def check_price_units(price_c, market_slug, confirmed=False,
                      allow_unverified=False):
    """Dollars-vs-cents tripwire at booking time.

 Returns an error string (caller fails) or None. See the construction
 comment above UNIT_DIRECT_TOL_C. `confirmed` (--confirm-cents) is the
 operator's explicit assertion "this price is in cents": it clears the
 no-quote and ambiguity rejections, never the 100x-confusion smoking gun.
 `allow_unverified` keeps the exit path fail-open on a dark feed —
 loss-capping is never blocked by missing telemetry (cmd_exit only).
 """
    cached = poller_price_cents(market_slug)
    if cached is None:
        if confirmed or allow_unverified:
            return None
        return (f"no poller quote for {market_slug} — units unverifiable; "
                f"add it to WATCHLIST.json or re-run with --confirm-cents")
    direct = abs(price_c - cached) <= UNIT_DIRECT_TOL_C
    confused = abs(price_c * 100.0 - cached) <= UNIT_CONFUSION_TOL_C
    if confused and direct:
        if confirmed:
            return None
        return (f"price {price_c}c is AMBIGUOUS against the poller quote "
                f"{cached}c for {market_slug}: reads as {price_c}c or "
                f"${price_c} (= {price_c * 100:g}c). --price takes CENTS; "
                f"re-run with --confirm-cents if you mean {price_c}c")
    if confused:
        return (f"price {price_c}c is ~100x below the poller quote "
                f"{cached}c for {market_slug} — did you pass DOLLARS? "
                f"--price takes CENTS ({cached} = {cached}c)")
    return None


def cmd_book(a):
    cfg = DESKS[a.desk]
    entries = load_ledger()
    opens = open_positions(entries)
    today = now_cdt().date().isoformat()
    # Rejection-log context (proposer contract): every REJECT on the booking
    # path is recorded with its reason — never silently clipped.
    rctx = {"action": "book", "desk": a.desk, "market": a.market,
            "proposer_id": getattr(a, "proposer", "") or ""}

    # Cents/dollars by construction (hardened repair #2): the
    # single choke point parse_price_cents decides the unit; check_price_units
    # trips the 100x dollars-passing error, the low-price ambiguity case, and
    # the no-quote case against the poller quote. (The old inline
    # `0 < price < 100` check could not catch 0.87-as-dollars — and 0.87c
    # is a legitimate longshot price, so the value alone can't decide.)
    try:
        price_c = parse_price_cents(a.price, "--price")
    except ValueError as e:
        return fail(str(e), rctx)
    if not (0 < a.p < 1):
        return fail("p must be 0-1 (exclusive)", rctx)
    unit_err = check_price_units(price_c, a.market,
                                 confirmed=getattr(a, "confirm_cents", False))
    if unit_err:
        return fail(unit_err, rctx)

    # Phase 1.2: solvable-universe filter at booking time. A
    # settled market is never a candidate — neither the optimizer nor this
    # path may solve on ghosts. (open_positions already excludes settled
    # markets from exposure counts; this closes the booking door itself.)
    if a.market in settled_markets():
        return fail(f"{a.market} is settled (settled.json) — removed from the "
                    "solvable universe, booking refused", rctx)

    # Driver declaration (the operator's concentration flag): --driver is
    # REQUIRED and must be a key in the framework-owned taxonomy. Missing/unknown
    # driver or an unreadable taxonomy REJECTs — the book path fails closed
    # rather than booking blind. Directives must declare it too (for tagging)
    # but are exempt from the cap below.
    drivers = load_drivers()
    if drivers is None:
        return fail("driver taxonomy unreadable "
                    f"({DRIVER_TAXONOMY_PATH}) — bookings halted until the framework "
                    "restores it", rctx)
    drv = (a.driver or "").strip().lower()
    if not drv:
        return fail("--driver is required "
                    "(see hidden_files/driver_taxonomy.json)", rctx)
    if drv not in drivers:
        return fail(f"--driver '{drv}' not in taxonomy "
                    "(see hidden_files/driver_taxonomy.json)", rctx)

    # Mikiri thesis schema (D-003, the operator's directive): every thesis
    # must name the loser and tag the initiative. The opponent must be READ
    # before the duel is joined — an unreadable opponent fails validation,
    # and the rejection log is the unreadable-opponent log. Uniform schema:
    # directives declare for tagging too (the operator's orders are still exempt
    # from the EV gate and caps, per the existing rules below).
    loser = (a.loser or "").strip()
    if len(loser) < MIKIRI_MIN_LOSER_LEN:
        return fail("mikiri: --loser is required — name the source of the "
                    "mispricing (who is wrong on the other side and why). "
                    "An unreadable opponent cannot be booked.", rctx)
    sen = (a.sen or "").strip()
    if sen not in SEN_CHOICES:
        return fail("mikiri: --sen is required — one of "
                    f"{', '.join(SEN_CHOICES)} (ken_no_sen=originate, "
                    "tai_no_sen=fade the attack, tai_tai_no_sen=join the "
                    "motion). An untagged initiative cannot be graded.", rctx)

    explore = False  # X exploration account tags its originated rows
    if a.desk == "X" and not a.directive:
        # X exploration account (recharter, the operator's directive;
        # breadth-first): no EV/mikiri gate — the gate is the
        # assumed-risk model under test. The honesty gates above (price units,
        # settled universe, driver taxonomy, thesis schema) still bind.
        # kelly_size runs for edge_pts and win_p display only; the target
        # clip is the charter breadth size, depth-capped by the fill engine
        # below. Family-correlation and driver-concentration caps do not bind
        # X (exploration freedom; driver/family still declared for the record).
        _, edge_pts, win_p = kelly_size(a.side, price_c, a.p,
                                        cfg["bankroll"], cfg["cap"],
                                        cfg["fraction"], None)
        size = X_TARGET_TRADE_USD
        eff_n, mikiri_exempt, explore = None, None, True
    elif not a.directive:
        # Mikiri EV gate (D-003): the refusal bar is confidence-bounded.
        # sigma=None means the desk is unreadable (eff_n below threshold) —
        # cold-start regime: the static gate applies (today's behavior), the
        # receipt is tagged mikiri_exempt, and the exemption dies permanently
        # once the desk's eff_n reaches MIKIRI_MIN_EFF_N. The first duels are
        # calibration-building, labeled as such, never silent.
        eff_n, sigma_fn = desk_calibration(a.desk)
        sigma = sigma_fn(a.p) if sigma_fn else None
        mikiri_exempt = None
        if sigma is None:
            mikiri_exempt = (f"cold-start eff_n={eff_n:.1f}"
                             f"<{MIKIRI_MIN_EFF_N:g}")
        size, edge_pts, win_p = kelly_size(a.side, price_c, a.p,
                                          cfg["bankroll"], cfg["cap"],
                                          cfg["fraction"], sigma)
        if size is None:
            if edge_pts <= ERROR_BAND * 100:
                if sigma is not None:
                    penalty_pts = MIKIRI_K * sigma * 100
                    return fail(f"mikiri gate: margin {edge_pts:+.1f}pts < "
                                f"5pt band (calibration penalty "
                                f"{penalty_pts:.1f}pts, eff_n={eff_n:.1f}) "
                                f"— NO BET", rctx)
                return fail(f"EV gate: edge {edge_pts:+.1f}pts inside 5pt band — NO BET", rctx)
            return fail(f"below minimum meaningful stake ($0.10) — edge too thin — NO BET", rctx)
    else:
        size, edge_pts = 1.0, None
        win_p = a.p if a.side == "yes" else 1.0 - a.p
        eff_n, mikiri_exempt = None, None

    # D-001 K1-bis interim regime (R HUNT #2 adjudicated): a desk
    # that fired K1-bis (majority of trailing-30d bookings mikiri-exempt —
    # Kelly-sizing on uncalibrated p's) books flat $0.10 minimum stakes until
    # its eff_n reaches MIKIRI_MIN_EFF_N. The EV/mikiri gates above still
    # apply — the regime de-risks sizing, never bypasses selection.
    # Directives are exempt: the regime binds the desk's origination, never
    # The operator's orders. Clearance is evaluated here, at booking time, so the
    # regime lifts itself the moment calibration data exists.
    k1bis_interim = False
    if not a.directive:
        interim = load_interim_regime().get(a.desk)
        if interim and interim.get("regime") == "flat-0.10":
            if eff_n is not None and eff_n >= MIKIRI_MIN_EFF_N:
                clear_interim_regime(
                    a.desk,
                    reason=(f"eff_n={eff_n:.1f} reached {MIKIRI_MIN_EFF_N:g} — "
                            f"cold-start over, Kelly sizing restored"))
            else:
                size = 0.10
                k1bis_interim = True

    desk_opens = [e for e in opens if e["desk"] == a.desk]
    if len(desk_opens) >= cfg["max_open"]:
        return fail(f"cap: {a.desk} already has {len(desk_opens)} open (max {cfg['max_open']})", rctx)
    if not a.directive:
        new_today = [e for e in entries
                     if e.get("action") == "book" and e["desk"] == a.desk
                     and not e.get("directive") and not e.get("shadow_of")
                     and e["ts_cdt"][:10] == today]
        if len(new_today) >= cfg["max_new_day"]:
            return fail(f"cap: {a.desk} daily new-trade cap reached "
                        f"({len(new_today)}/{cfg['max_new_day']}) — allowance, not quota", rctx)

    derived = derive_family(a.market)
    declared = (a.family or "").strip().lower()
    fams = {derived} | ({declared} if declared else set())
    # X exploration account: family-correlation does not bind (charter) —
    # exploring the same event family (even the opposite side) is the job.
    # Family is still declared for the research record.
    for e in opens:
        if e["desk"] == "X" or a.desk == "X":
            continue
        # recompute derived from the slug every time — never trust a stored tag
        other = {derive_family(e.get("market", "")), e.get("family_declared", "")} - {""}
        if fams & other:
            return fail(f"correlation: event family '{(fams & other).pop()}' already open "
                        f"({e['receipt_id']}, desk {e['desk']}) — one slot per cluster", rctx)

    # Driver-concentration gate (the operator's flag): max DRIVER_CAP open
    # positions per macro driver across M/S/F/Q/C. X rows exempt (shadows
    # mirror by design; originated explorations have charter freedom — driver
    # still declared for the research record). DIRECTIVES ARE NOT EXEMPT —
    # the cap is absolute (ruling: "directive exemptions cannot
    # bypass this absolute cap"); the operator's orders declare --driver for tagging
    # and are still rejected on a full driver. Counts backfilled
    # grandfathered rows too — the 3 iran-geopolitics positions open at gate
    # launch stay, but a 4th pile-on is blocked.
    holders = [e for e in opens
               if e["desk"] != "X"
               and (e.get("driver") or "").strip().lower() == drv]
    if a.desk != "X" and len(holders) >= DRIVER_CAP:
        return fail(f"driver-concentration: '{drv}' already has "
                    f"{len(holders)} open "
                    f"({', '.join(e['receipt_id'] for e in holders)}) — "
                    f"max {DRIVER_CAP} per driver across desks; a third "
                    "pile-on is blocked", rctx)

    # Honest fills (the reviewer's ordered plan, the operator approved "breadth
    # first"): the worker's --price is the LIMIT; this path walks the live
    # book and executes at VWAP. Replaces the 0.5c worker-applied haircut —
    # slippage now grows with size by construction, and each clip is capped
    # at the depth the book absorbs within 1c of the touch. Entries fail
    # closed without a depth snapshot: an assumed fill is an invented fill.
    # (Placed after the cap/family/driver gates: fail fast on those before
    # spending the book fetch.)
    req_size = size
    limit_c = price_c
    try:
        fill = entry_fill(a.market, a.side, size, limit_c)
    except FillError as e:
        return fail(f"honest-fill: {e}", rctx)
    price_c = fill["vwap_c"]
    size = fill["filled_usd"]

    rid = next_receipt(entries)
    rec = {"action": "book", "receipt_id": rid, "ts_cdt": now_cdt().isoformat(),
           "desk": a.desk, "market": a.market, "side": a.side,
           "price_c": price_c, "p_yes": a.p, "win_p": round(win_p, 4),
           "edge_pts": round(edge_pts, 2) if edge_pts is not None else None,
           "size_usd": size, "family_declared": declared,
           # Honest-fill record: price_c/size_usd are EXECUTED
           # (VWAP / filled). The request and the economics around it:
           "attempted_usd": round(req_size, 2),
           "unfilled_usd": round(req_size - size, 2),
           "limit_c": limit_c,
           "fee_usd": fill["fee_usd"],
           "fee_rate": fill["fee_rate"],
           "fee_category": fill["fee_category"],
           "fee_unknown": fill["fee_unknown"],
           "depth_1c_usd": fill["depth_1c_usd"],
           "fill_venue": fill["fill_venue"],
           # Fill-model regime tag: scoring panels split on
           # this. Rows without the tag are v1 (0.5c haircut, no fees).
           "fill_model": "v2-bookwalk",
           "family_derived": derived, "driver": drv,
           "directive": bool(a.directive),
           # D-001 K1-bis: True when this booking was sized by the interim
           # flat-$0.10 regime rather than Kelly.
           "k1bis_interim": k1bis_interim,
           # Mikiri thesis schema (D-003): the named loser and the initiative
           # tag. Calibration is graded per (desk, sen) — see SPEC.md.
           "loser": loser, "sen": sen,
           # Proposer contract: size_suggestion is ADVISORY ONLY — the script's
           # Kelly computation above is the only size that executes. The
           # suggestion is logged so the proposer's sizing judgment can be scored.
           "proposer_id": rctx["proposer_id"],
           "proposer_size_usd": getattr(a, "size_suggest", None),
           # D-004 trap audit join: which pre-registered tripwire (if any)
           # authorized this booking attempt. Empty for loop-direct books.
           "trap_id": getattr(a, "trap_id", "") or "",
           # Display fields for the PAPER.md projection (ruling #3).
           # The projection FAILS LOUDLY on a missing thesis / ev_gate — these
           # are recorded here, at booking time, never hand-edited later.
           "thesis": (a.thesis or "").strip(),
           "ev_gate": ("directive" if a.directive
                       else ("explore" if explore
                             else (a.ev_gate or "").strip())),
           "status": "open", "note": a.note or ""}
    if a.nominate_real:
        if a.r_rating not in ("HARD", "SOFT", "MISS"):
            return fail("--nominate-real requires --r-rating HARD|SOFT|MISS")
        rec["nominated_real"] = True
        rec["r_rating"] = a.r_rating
    # Mikiri audit trail (D-003): record the bound that applied. Exempt rows
    # are the calibration-building duels — visible, countable, expirable.
    # X exploration rows carry the explore tag instead (no EV gate applied).
    if a.desk == "X" and not a.directive:
        rec["explore"] = True
    elif not a.directive:
        if mikiri_exempt:
            rec["mikiri_exempt"] = mikiri_exempt
        else:
            rec["mikiri"] = {"eff_n": round(eff_n, 2),
                             "sigma": round(sigma, 4),
                             "penalty_pts": round(MIKIRI_K * sigma * 100, 2),
                             "k": MIKIRI_K}
    append(rec)
    log_decision_features(a, rid, rec["ts_cdt"])
    print(f"ACCEPT {rid} | {a.desk} {a.side} {a.market} @ {price_c}c VWAP "
          f"| fill ${size:.2f} of ${req_size:.2f} attempted "
          f"(depth_1c ${fill['depth_1c_usd']:.2f}, fee ${fill['fee_usd']:.2f} "
          f"@{fill['fee_rate']}/{fill['fee_category']}"
          f"{' fee_unknown' if fill['fee_unknown'] else ''})"
          + (" | K1-bis interim flat-$0.10" if k1bis_interim else "")
          + (f" | edge {edge_pts:+.1f}pts" if edge_pts is not None else " | directive")
          + f" | driver={drv} | sen={sen}"
          + (f" | {mikiri_exempt}" if not a.directive and mikiri_exempt else ""))
    return 0


def cmd_shadow(a):
    entries = load_ledger()
    opens = open_positions(entries)
    src = next((e for e in entries
                if e.get("receipt_id") == a.shadow_of and e.get("action") == "book"), None)
    if src is None:
        return fail(f"shadow source {a.shadow_of} not found in ledger")
    if src.get("directive"):
        return fail("X never shadows directives")
    if src.get("desk") == "X":
        return fail("X never shadows X — no shadow chains")
    if any(e["desk"] == "X" and e["market"] == src["market"]
           for e in opens):
        return fail(f"X already shadows {src['market']} — never doubles a market")
    # Cents/dollars by construction: shadow had NO price
    # validation at all — a raw argparse float flowed straight into price_c.
    try:
        price_c = parse_price_cents(a.price, "--price")
    except ValueError as e:
        return fail(str(e))
    unit_err = check_price_units(price_c, src["market"],
                                 confirmed=getattr(a, "confirm_cents", False))
    if unit_err:
        return fail(unit_err)
    # Honest fills: shadows walk the book like any entry.
    # --attempted is the request; the fill is depth-capped at 1c of touch.
    try:
        fill = entry_fill(src["market"], a.side, a.attempted, price_c)
    except FillError as e:
        return fail(f"honest-fill: {e}")
    rid = next_receipt(entries)
    rec = {"action": "book", "receipt_id": rid, "ts_cdt": now_cdt().isoformat(),
           "desk": "X", "market": src["market"], "side": a.side,
           "price_c": fill["vwap_c"], "size_usd": fill["filled_usd"],
           "attempted_usd": round(a.attempted, 2),
           "unfilled_usd": round(a.attempted - fill["filled_usd"], 2),
           "limit_c": price_c,
           "fee_usd": fill["fee_usd"], "fee_rate": fill["fee_rate"],
           "fee_category": fill["fee_category"],
           "fee_unknown": fill["fee_unknown"],
           "depth_1c_usd": fill["depth_1c_usd"],
           "fill_venue": fill["fill_venue"],
           "fill_model": "v2-bookwalk",
           "shadow_of": a.shadow_of, "status": "open",
           "family_declared": src.get("family_declared", ""),
           "family_derived": src.get("family_derived", ""),
           # X mirrors the source's driver for audit visibility — X is exempt
           # from the driver-concentration cap by design (it never originates).
           "driver": src.get("driver", ""),
           # Mikiri (D-003): the shadow inherits the originator's read — X
           # never names its own loser or initiative.
           "loser": src.get("loser", ""), "sen": src.get("sen", ""),
           # Display fields for the PAPER.md projection (ruling #3): X's
           # EV-gate label derives as "sandbox"; the thesis is recorded here.
           "thesis": (a.thesis or "").strip(),
           "ev_gate": "sandbox",
           "note": a.note or ""}
    append(rec)
    print(f"ACCEPT {rid} | X shadows {a.shadow_of} ({src['market']}) "
          f"| fill ${fill['filled_usd']:.2f} of ${a.attempted:.2f} attempted "
          f"@ {fill['vwap_c']}c VWAP (fee ${fill['fee_usd']:.2f})")
    return 0


def poller_price_cents(market_slug):
    """Resolve a ledger market slug to poller-cache cents.

 slug -> WATCHLIST key -> nightwatch-prices.json px. Fail-closed: None
 when unresolvable (never guess a price for an exit).
 """
    try:
        wl = json.load(open(os.path.join(ROOT, "desks", "WATCHLIST.json")))
        markets = wl.get("markets", {})
    except (OSError, json.JSONDecodeError):
        return None
    key = None
    if market_slug in markets:
        key = market_slug
    else:
        for k, m in markets.items():
            if isinstance(m, dict) and m.get("slug") == market_slug:
                key = k
                break
    if key is None:
        return None
    try:
        px = json.load(open(HOOK_PRICES))[key]["px"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None
    if not isinstance(px, (int, float)) or not (0.0 <= px <= 1.0):
        return None
    return int(round(px * 100))


def cmd_exit(a):
    entries = load_ledger()
    opens = open_positions(entries)
    tgt = next((e for e in opens if e["receipt_id"] == a.receipt), None)
    if tgt is None:
        return fail(f"open receipt {a.receipt} not found")
    exit_price = a.exit_price
    note = a.note or ""
    if a.auto_price:
        # The lifeboat: price off the coarse 90s poller when the stream is
        # dark (or whenever the operator asks). Provenance is tagged.
        exit_price = poller_price_cents(tgt["market"])
        if exit_price is None:
            return fail(f"auto-price: no poller quote for {tgt['market']}; "
                        f"pass --exit-price explicitly")
        tags = ["price_source:poller"]
        if stream_watch is not None and stream_watch.stream_dark_for_exits():
            tags.append("degraded:stream_dark")
        note = (note + " " + " ".join(tags)).strip()
    elif exit_price is None:
        return fail("exit requires --exit-price or --auto-price")
    # Cents/dollars by construction (hardened repair #2): a
    # dollars exit price would corrupt realized P&L exactly like a dollars
    # booking corrupts sizing. --auto-price is already int cents from the
    # poller. Deliberate asymmetry: allow_unverified=True — a dark feed must
    # never block loss-capping; the operator passing --exit-price explicitly
    # is asserting the price. New risk (book/shadow) has no such pass.
    try:
        exit_price = parse_price_cents(exit_price, "--exit-price")
    except ValueError as e:
        return fail(str(e))
    unit_err = check_price_units(exit_price, tgt["market"],
                                 confirmed=getattr(a, "confirm_cents", False),
                                 allow_unverified=True)
    if unit_err:
        return fail(unit_err)
    rec = {"action": "exit", "receipt_id": a.receipt,
           "ts_cdt": now_cdt().isoformat(), "exit_price_c": exit_price,
           "note": note}
    entry = tgt["price_c"]
    shares = tgt["size_usd"] / (entry / 100.0)
    entry_fee = tgt.get("fee_usd", 0.0) or 0.0
    # Honest exit: walk the bid side when a snapshot exists, so
    # exit slippage is measured, not haircut-estimated. Fail-open: a dark
    # book must never block loss-capping — fall back to the worker/poller
    # price, tagged unverifiable. Explicit --exit-price acts as the limit
    # (never sell below the asserted price); --auto-price takes the book.
    exit_fee_usd, exit_fee_rate = 0.0, 0.0
    exit_fee_cat, exit_fee_unknown, exit_basis = "unknown", True, "unverifiable"
    try:
        xf = exit_fill(tgt["market"], tgt["side"], shares,
                       None if a.auto_price else exit_price)
        exit_price = xf["vwap_c"]
        exit_fee_usd, exit_fee_rate = xf["fee_usd"], xf["fee_rate"]
        exit_fee_cat, exit_fee_unknown = xf["fee_category"], xf["fee_unknown"]
        exit_basis = "book-walk"
        rec["exit_price_c"] = exit_price
    except FillError:
        pass
    # Side-agnostic P&L: the ledger prices the purchased token, so a No
    # exited below its entry price is a LOSS, full stop. (: the old
    # No-branch computed (entry - exit_price) and printed +$6.77 on a -$6.77
    # exit. Ledger data was unaffected — the receipt carries exit_price_c
    # only — but the console lied. Now the print and the math agree.)
    #: P&L is net of entry + exit taker fees.
    move = exit_price - entry
    pnl = round(move / 100.0 * shares - entry_fee - exit_fee_usd, 2)
    rec["realized_pnl_usd"] = pnl
    rec["exit_basis"] = exit_basis
    rec["exit_fee_usd"] = exit_fee_usd
    rec["exit_fee_rate"] = exit_fee_rate
    rec["fill_model"] = "v2-bookwalk"
    # X-shadow cascade (R doctrine-hunt #3): an X shadow is a
    # mirror of its originator's thesis — when the originator exits, every
    # open shadow of it exits at the same price in the same atomic write.
    # Before this, shadows orphaned on originator exit and stayed "open"
    # forever, invisible to the hourly audit (desk X is skipped there).
    # Shadows on a mismatched market are a ledger-corruption signal: they are
    # left open and LOUDLY warned, never silently exited at a wrong price —
    # the audit ORPHAN check keeps flagging them until hand-remediated.
    new_entries = [rec]
    closures = {a.receipt: {
        "close_action": "exit", "close_ts_cdt": rec["ts_cdt"],
        "close_price_c": exit_price, "realized_pnl_usd": pnl}}
    for s in opens:
        if s.get("desk") != "X" or s.get("shadow_of") != a.receipt:
            continue
        if s.get("market") != tgt["market"]:
            print(f"WARN: X shadow {s['receipt_id']} market "
                  f"{s.get('market')} != originator {tgt['market']} — "
                  f"left open; audit will flag ORPHAN")
            continue
        sentry = s["price_c"]
        sshares = s["size_usd"] / (sentry / 100.0)
        s_entry_fee = s.get("fee_usd", 0.0) or 0.0
        s_exit_fee = (round(fe.taker_fee_usd(sshares, exit_price / 100.0,
                                             exit_fee_rate), 2)
                      if not exit_fee_unknown else 0.0)
        spnl = round((exit_price - sentry) / 100.0 * sshares
                     - s_entry_fee - s_exit_fee, 2)
        new_entries.append({
            "action": "exit", "receipt_id": s["receipt_id"],
            "ts_cdt": rec["ts_cdt"], "exit_price_c": exit_price,
            "realized_pnl_usd": spnl,
            "exit_basis": exit_basis, "exit_fee_usd": s_exit_fee,
            "fill_model": "v2-bookwalk",
            "note": (f"cascade from {a.receipt} " + note).strip()})
        closures[s["receipt_id"]] = {
            "close_action": "exit", "close_ts_cdt": rec["ts_cdt"],
            "close_price_c": exit_price, "realized_pnl_usd": spnl}
    # Terminal closure (the operator's ruling #2): the book row itself is
    # mutated to closed at rest — close action, timestamp, close price, and
    # final realized P&L. The exit receipt remains the append-only audit trail.
    ledger_append_and_close(new_entries, closures)
    print(f"EXIT {a.receipt} | {tgt['desk']} {tgt['market']} "
          f"{entry}c -> {exit_price}c | approx P&L ${pnl:+.2f}")
    for s in opens:
        if s.get("desk") == "X" and s.get("shadow_of") == a.receipt \
                and s["receipt_id"] in closures:
            sc = closures[s["receipt_id"]]
            print(f"CASCADE {s['receipt_id']} | X shadow of {a.receipt} "
                  f"exited @ {exit_price}c "
                  f"| approx P&L ${sc['realized_pnl_usd']:+.2f}")
    return 0


def normalize_outcome(raw):
    """YES|NO canonical form. Returns None on garbage (fail, don't guess)."""
    s = str(raw).strip().lower()
    if s in ("yes", "y", "true", "1"):
        return "YES"
    if s in ("no", "n", "false", "0"):
        return "NO"
    return None


def realized_pnl(side, price_c, size_usd, outcome):
    """P&L of holding to resolution. Win: shares * (100 - entry); else -size."""
    won = (side == "yes") == (outcome == "YES")
    if won:
        shares = size_usd / (price_c / 100.0)
        return round(shares * (1 - price_c / 100.0), 2)
    return round(-size_usd, 2)


def match_ws_keys(ws_pos, receipt):
    """worker_state position keys matching a ledger receipt — the keys
 settle_write_worker_state is authorized to DELETE.

 Exact key == receipt_id wins outright. The desk+side+entry-proximity
 heuristic is only a fallback for legacy keys that predate receipt-id
 keying — and it requires a recorded entry within 2c. A bare desk+side
 match with entry=None is too weak for a destructive operation.
 (: the ghost settle for bk-bootstrap-01 matched
 bk-bootstrap-02 on a bare C/no with entry=None and DELETED a live,
 unrelated position. The audit may reconcile weakly to *detect* drift;
 deletion requires strong evidence.)
 """
    rid = receipt.get("receipt_id")
    if rid in ws_pos:
        return [rid]
    out = []
    for key, p in ws_pos.items():
        if p.get("desk") != receipt.get("desk"):
            continue
        if str(p.get("side", "")).lower() != str(receipt.get("side", "")).lower():
            continue
        entry = p.get("entry")
        if entry is None:
            continue  # bare desk+side never authorizes deletion
        if abs(receipt["price_c"] / 100.0 - entry) >= 0.02:
            continue
        out.append(key)
    return out


def load_json_doc(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def write_json_doc(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")


def settle_write_ledger(targets, outcome, pnls, note):
    """Append one `settle` receipt per settled book row AND terminally close
 the book rows (the operator's ruling #2 — terminal closure): status,
 outcome, timestamp, and final realized P&L mutate onto the row itself, so
 the ledger reads absolute reality at rest. The settle receipts remain the
 append-only audit trail. Atomic with the row closures."""
    stamp = now_cdt().isoformat()
    receipts, closures = [], {}
    for e, (pnl, method) in zip(targets, pnls):
        receipts.append({"action": "settle", "receipt_id": e["receipt_id"],
                         "ts_cdt": stamp, "market": e["market"],
                         "desk": e["desk"], "side": e["side"],
                         "outcome": outcome, "realized_pnl_usd": pnl,
                         "pnl_method": method, "note": note or ""})
        closures[e["receipt_id"]] = {
            "close_action": "settle", "close_ts_cdt": stamp,
            "close_outcome": outcome, "realized_pnl_usd": pnl}
    ledger_append_and_close(receipts, closures)


def settle_write_settled_json(market, outcome, resolved_cdt, evidence, rows):
    doc = load_json_doc(SETTLED_PATH, {})
    doc.setdefault("settled", {})
    doc["settled"][market] = {
        "outcome": outcome,
        # yes_won is what brier.py outcome_for reads — without it the
        # pending shadow rows and PAPER.md ledger rows never grade.
        "yes_won": outcome == "YES",
        "resolved_cdt": resolved_cdt,
        "evidence": evidence or "",
        "settled_by": "book_trade.py settle",
        "rows": rows,
    }
    write_json_doc(SETTLED_PATH, doc)


def settle_write_brier_shadow(market, targets, stamp):
    """File p-bearing rows into brier_shadow.json pending so they grade at
 resolution. Directive rows (no p by design) and X shadows (unscored
 sandbox) never enter — same rule as the mechanical-exit path."""
    doc = load_json_doc(BRIER_SHADOW, {"pending": [], "scored": []})
    doc.setdefault("pending", [])
    n = 0
    for e in targets:
        win_p = e.get("win_p")
        if win_p is None or e.get("directive") or e.get("desk") == "X":
            continue
        doc["pending"].append({
            "market": market, "desk": e["desk"], "side": e["side"].title(),
            "p": round(win_p, 4), "settle_time": stamp,
            "note": f"settled via book_trade.py settle ({e['receipt_id']})",
        })
        n += 1
    write_json_doc(BRIER_SHADOW, doc)
    return n


def log_decision_features(a, rid, ts_cdt):
    """ML instrumentation (the operator: "use ML if you think best"):
 snapshot the funnel candidate's features at decision time into
 hidden_files/decision_features.jsonl (append-only JSONL). Purely additive —
 it never fails a booking and touches no gate. Joins to brier_shadow.json
 scored rows on (market, desk, side) when the future calibration/proposer
 trainer runs. funnel=null when the thesis didn't come from a funnel
 candidate (worker passes --funnel-event only then)."""
    try:
        snap = None
        want = (getattr(a, "funnel_event", "") or "").strip().lower()
        if want:
            doc = load_json_doc(FUNNEL_CACHE, {})
            cands = doc.get("candidates") or []
            hit = next((c for c in cands
                        if str(c.get("slug", "")).lower() == want), None)
            if hit is None:
                mkt = (a.market or "").strip().lower()
                for c in cands:
                    tms = c.get("top_markets") or []
                    if any(str(tm.get("slug", "")).lower() in (want, mkt)
                           for tm in tms):
                        hit = c
                        break
            if hit is not None:
                pxs = [p for tm in (hit.get("top_markets") or [])
                       for p in (tm.get("px") or [])
                       if isinstance(p, (int, float))]
                hrs = None
                try:
                    ends = hit.get("ends")
                    if ends:
                        dt = datetime.fromisoformat(str(ends).replace("Z", "+00:00"))
                        hrs = (dt - datetime.now(timezone.utc)).total_seconds() / 3600
                except Exception:
                    hrs = None
                snap = {"event_slug": hit.get("slug"),
                        "category": hit.get("category"),
                        "vol24h": hit.get("vol24h"),
                        "hours_to_res": round(hrs, 1) if hrs is not None else None,
                        "n_top_markets": len(hit.get("top_markets") or []),
                        "px_spread": round(max(pxs) - min(pxs), 4) if pxs else None}
        line = {"receipt_id": rid, "ts_cdt": ts_cdt, "desk": a.desk,
                "market": a.market, "side": a.side, "p_yes": a.p,
                "driver": getattr(a, "driver", "") or "",
                "sen": getattr(a, "sen", "") or "",
                "proposer_id": getattr(a, "proposer", "") or "",
                "funnel": snap}
        with open(DECISION_FEATURES, "a") as f:
            f.write(json.dumps(line) + "\n")
    except Exception as e:  # instrumentation must never break booking
        print(f"warn: decision-features log failed ({e})", file=sys.stderr)


def settle_write_worker_state(targets):
    """Remove settled positions from worker_state.json. Returns removed keys.

 Schema note: production worker_state.json carries
 `positions` as a LIST of dicts with a 'key' field (the hourly worker's
 schema), while older fixtures/tests use a dict keyed by receipt id.
 Normalize the list to the dict schema the matcher expects, convert back
 after. (Found when the f-anthropic-no settle crashed mid-write on
 `ws_pos.items` — the ledger and settled.json were already written;
 the crash left the worker_state/WATCHLIST cleanup incomplete.)
 """
    ws = load_json_doc(WS_PATH, {})
    ws_pos = ws.get("positions", {})
    was_list = isinstance(ws_pos, list)
    if was_list:
        ws_pos = {p.get("key", "idx%d" % i): p
                  for i, p in enumerate(ws_pos) if isinstance(p, dict)}
    removed = []
    for e in targets:
        for key in match_ws_keys(ws_pos, e):
            ws_pos.pop(key, None)
            removed.append(key)
    ws["positions"] = ([p for p in ws_pos.values()] if was_list else ws_pos)
    write_json_doc(WS_PATH, ws)
    return removed


def settle_write_watchlist(market, outcome, stamp_short):
    """Drop the `position` field from WATCHLIST markets with this slug; the
 market stays watched, the note records the settlement."""
    wl = load_json_doc(WATCHLIST_PATH, {})
    markets = wl.get("markets", {})
    touched = []
    for key, m in markets.items():
        if not isinstance(m, dict) or m.get("slug") != market:
            continue
        if "position" in m:
            m.pop("position", None)
            old = (m.get("note") or "").strip()
            m["note"] = (f"SETTLED {stamp_short}: resolved {outcome}. "
                         f"Position closed; removed from book."
                         + (f" {old}" if old else ""))
            touched.append(key)
    write_json_doc(WATCHLIST_PATH, wl)
    return touched


def _seg_norm(seg_head):
    s = seg_head.strip().lower()
    if s.endswith("-no"):
        s = s[:-3]
    return s


def settle_write_status(removed_ws_keys):
    """Patch the '- Open positions (N):' heartbeat line: drop segments for
 settled keys, decrement N. Best-effort — the hourly render regenerates
 this file from worker_state.json anyway."""
    if not removed_ws_keys:
        return True, "no worker_state positions removed — line untouched"
    try:
        with open(STATUS_PATH) as f:
            lines = f.readlines()
    except OSError:
        return False, "STATUS.md unreadable"
    for i, line in enumerate(lines):
        if not line.startswith("- Open positions ("):
            continue
        m = re.match(r"- Open positions \((\d+)\):\s*(.*)", line.rstrip("\n"))
        if not m:
            return False, "positions line has unexpected format"
        n, rest = int(m.group(1)), m.group(2)
        segs = [s for s in rest.split(" | ") if s.strip()]
        dropped = 0
        keep = []
        for seg in segs:
            head = _seg_norm(seg.split()[0])
            hit = any(head == _seg_norm(k) or _seg_norm(k).startswith(head + "-")
                      for k in removed_ws_keys)
            if hit:
                dropped += 1
            else:
                keep.append(seg)
        lines[i] = f"- Open positions ({n - dropped}): {' | '.join(keep)}\n"
        with open(STATUS_PATH, "w") as f:
            f.writelines(lines)
        return True, f"dropped {dropped} segment(s)"
    return False, "no '- Open positions' line found"


def verify_settle(market, receipt_ids):
    """Post-write consistency: no orphans either direction."""
    issues = []
    doc = load_json_doc(SETTLED_PATH, {})
    entry = (doc.get("settled") or {}).get(market)
    if not entry:
        issues.append("settled.json missing the market entry")
    elif "yes_won" not in entry:
        issues.append("settled.json entry lacks yes_won — brier.py cannot grade it")
    entries = load_ledger()
    still_open = [e for e in open_positions(entries) if e.get("market") == market]
    if still_open:
        issues.append("ledger still shows open: "
                      + ", ".join(e["receipt_id"] for e in still_open))
    settled_ids = {e["receipt_id"] for e in entries if e.get("action") == "settle"}
    for rid in receipt_ids:
        if rid not in settled_ids:
            issues.append(f"ledger missing settle receipt for {rid}")
    return issues


def fetch_gamma_market(slug):
    """Phase 1.2: fetch the gamma-api market payload for a .com slug.

 Returns the market dict, or None on any transport/parse failure.
 NIGHTWATCH_GAMMA_STUB (tests only): path to a JSON file mapping slug ->
 payload; when set, the network is bypassed entirely.
 """
    stub = os.environ.get("NIGHTWATCH_GAMMA_STUB")
    if stub:
        try:
            with open(stub) as f:
                return json.load(f).get(slug)
        except (OSError, json.JSONDecodeError):
            return None
    import urllib.request
    url = "https://gamma-api.polymarket.com/markets?slug=" + slug
    # gamma-api 403s the default urllib User-Agent (observed) —
    # without this header every .com lookup fails and entries fail closed.
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "nightwatch-funnel/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return None
    return data[0] if data else None


class FillError(Exception):
    """No honest fill available. Entries fail closed on this; exits fall back
 (fail-open) because loss-capping must never be blocked by a dark feed."""


def fetch_book_snapshot(market_slug):
    """Fetch a live order-book snapshot for honest fills.

 Returns (venue, bids, asks, aux): bids/asks are [(price01, size_shares)]
 best-first; aux carries tags/token metadata. Raises FillError when no
 snapshot exists.

 Resolution order: NIGHTWATCH_BOOK_STUB (tests: JSON slug -> {venue, bids,
 asks, tags}) -> .com via gamma clobTokenIds -> CLOB /book -> .us via the
 public gateway book endpoint. The venue is discovered by which API
 answers; nothing is assumed from the slug.
 """
    stub = os.environ.get("NIGHTWATCH_BOOK_STUB")
    if stub:
        try:
            with open(stub) as f:
                snap = json.load(f).get(market_slug)
        except (OSError, json.JSONDecodeError):
            snap = None
        if not snap:
            raise FillError(f"no depth snapshot for {market_slug} (stub)")
        bids = fe.normalize_levels(snap.get("bids"))
        asks = fe.normalize_levels(snap.get("asks"))
        aux = {"tags": snap.get("tags", [])}
        return snap.get("venue", "com"), bids, asks, aux

    # .com: gamma payload -> clobTokenIds ([yes, no]) -> CLOB book.
    payload = fetch_gamma_market(market_slug)
    if payload:
        tids = payload.get("clobTokenIds")
        if isinstance(tids, str):
            # gamma-api returns clobTokenIds as a JSON-encoded STRING, not a
            # list (observed); tids[0] on the raw string is "[",
            # which built a garbage token_id URL and 404'd every .com book.
            try:
                tids = json.loads(tids)
            except (json.JSONDecodeError, TypeError):
                tids = None
        if not tids:
            raise FillError(f".com {market_slug}: gamma payload has no "
                            "clobTokenIds — cannot walk the book")
        import urllib.request
        url = ("https://clob.polymarket.com/book?token_id=" + str(tids[0]))
        # CLOB also 403s the default urllib User-Agent (observed)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "nightwatch-funnel/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
        except Exception as e:
            raise FillError(f".com {market_slug}: CLOB book fetch failed "
                            f"({e})")
        bids = fe.normalize_levels(data.get("bids"))
        asks = fe.normalize_levels(data.get("asks"))
        return "com", bids, asks, {"tags": payload.get("tags", [])}

    # .us: public gateway book endpoint (unauthenticated).
    try:
        import polymarket_us as pmus
        raw = pmus.get_order_book(market_slug)
    except Exception as e:
        raise FillError(f"no depth snapshot for {market_slug}: .com gamma "
                        f"miss and .us book failed ({e})")
    bids = fe.normalize_levels((raw or {}).get("bids"))
    asks = fe.normalize_levels((raw or {}).get("asks"))
    if not bids and not asks:
        raise FillError(f".us {market_slug}: empty book response")
    return "us", bids, asks, {"tags": []}


def _fee_for(venue, tags, shares, vwap01):
    """(fee_usd, fee_rate, fee_category, fee_unknown) for a fill."""
    if venue == "us":
        rate, unknown, category = fe.FEE_RATE_US, False, "us"
    else:
        rate, unknown, category = fe.category_fee_rate(tags)
    fee = fe.taker_fee_usd(shares, vwap01, rate)
    return round(fee, 2), rate, category, unknown


def entry_fill(market, side, size_usd, limit_c):
    """Walk the live book for an entry (always a buy of the side's token).

 limit_c (cents) is the worker's --price, acting as the limit: nothing
 fills above it. The clip is additionally capped at the depth the book
 absorbs within 1c of the touch. Returns the fill record; raises FillError.
 """
    if fe is None:
        raise FillError("fill_engine unavailable — refusing rather than "
                        "booking at an unverified price")
    venue, bids, asks, aux = fetch_book_snapshot(market)
    if not asks:
        raise FillError(f"{venue} {market}: empty ask side — no honest fill")
    asks_asc = sorted(asks, key=lambda x: x[0])
    touch01 = asks_asc[0][0]
    if touch01 * 100.0 > limit_c + 1e-9:
        raise FillError(f"no depth within limit {limit_c}c "
                        f"(touch {touch01 * 100.0:.2f}c)")
    # The limit is a limit: a real limit order never fills above it. Filter
    # before the depth cap and the walk, so VWAP <= limit_c by construction.
    # This is also what keeps the EV/mikiri gate (evaluated at the limit
    # price) conservative: edge at the walked fill is always >= edge at the
    # gate price. (: the walk previously filled up to 1c above the
    # limit via the depth tolerance, overstating gate edge by up to ~1pt.)
    asks_asc = [a for a in asks_asc if a[0] * 100.0 <= limit_c + 1e-9]
    depth_1c = fe.depth_within_cents(asks_asc, touch01)
    capped = min(size_usd, depth_1c)
    w = fe.walk_book(asks_asc, capped)
    if w["filled_usd"] < fe.MIN_FILL_USD:
        raise FillError(f"depth within 1c of touch ${depth_1c:.2f} < $0.10 — "
                        "no honest fill")
    fee_usd, rate, category, unknown = _fee_for(
        venue, aux.get("tags"), w["shares"], w["vwap01"])
    return {"vwap_c": round(w["vwap01"] * 100, 2),
            "filled_usd": w["filled_usd"],
            "shares": w["shares"],
            "limit_c": limit_c,
            "fee_usd": fee_usd,
            "fee_rate": rate,
            "fee_category": category,
            "fee_unknown": unknown,
            "depth_1c_usd": depth_1c,
            "fill_venue": venue,
            "exhausted": w["exhausted"]}


def exit_fill(market, side, shares, limit_c=None):
    """Walk the bid side for an exit (selling the held token).

 limit_c (cents): don't sell below this (the worker's --exit-price).
 None = take the book as-is (--auto-price). Raises FillError when the
 book can't fill within the limit; the caller falls back fail-open.
 """
    if fe is None:
        raise FillError("fill_engine unavailable")
    venue, bids, asks, aux = fetch_book_snapshot(market)
    if not bids:
        raise FillError(f"{venue} {market}: empty bid side")
    levels = bids  # best-first descending already
    if limit_c is not None:
        levels = [l for l in levels if l[0] * 100.0 >= limit_c - 1e-9]
        if not levels:
            raise FillError(f"no bids within limit {limit_c}c")
    w = fe.walk_book_sell(levels, shares)
    if w["shares"] <= 0:
        raise FillError("zero fill on exit walk")
    fee_usd, rate, category, unknown = _fee_for(
        venue, aux.get("tags"), w["shares"], w["vwap01"])
    return {"vwap_c": round(w["vwap01"] * 100, 2),
            "proceeds_usd": w["proceeds_usd"],
            "shares": w["shares"],
            "fee_usd": fee_usd,
            "fee_rate": rate,
            "fee_category": category,
            "fee_unknown": unknown,
            "fill_venue": venue,
            "exhausted": w["exhausted"]}


def classify_gamma_resolution(payload):
    """Phase 1.2: classify a gamma-api market payload for resolution.

 Returns (status, yes_won_or_None, evidence). Pure function — no I/O.
 RESOLVED — closed with decisive outcomePrices ([1,0] => YES won,
 [0,1] => NO won). Only this status auto-settles.
 OPEN — venue reports the market still open.
 AMBIGUOUS — closed but the outcome is not decisive. Never auto-settled;
 goes to the human review queue (fail-closed on ambiguity).
 ERROR — payload missing/unreadable. Never auto-settled.
 """
    if not isinstance(payload, dict):
        return ("ERROR", None, "empty/unreadable venue payload")
    if not payload.get("closed"):
        return ("OPEN", None, "venue reports market open")
    try:
        prices = payload.get("outcomePrices")
        if isinstance(prices, str):
            prices = json.loads(prices)
        prices = [float(p) for p in prices]
    except (TypeError, ValueError):
        return ("AMBIGUOUS", None, "closed but outcomePrices unparseable")
    uma = payload.get("umaResolutionStatus", "?")
    if prices == [1.0, 0.0]:
        return ("RESOLVED", True, f"closed, uma={uma}, outcomePrices=[1,0]")
    if prices == [0.0, 1.0]:
        return ("RESOLVED", False, f"closed, uma={uma}, outcomePrices=[0,1]")
    return ("AMBIGUOUS", None,
            f"closed but indecisive prices={prices} uma={uma}")


def _resolve_review(market, detail):
    try:
        with open(RESOLVE_REVIEW, "a") as f:
            f.write(json.dumps({"ts_cdt": now_cdt().isoformat(),
                                "market": market, "detail": detail}) + "\n")
    except OSError:
        pass
    print(f"  review queued: {market} — {detail}")


def cmd_resolve_sweep(a):
    """Phase 1.2: detect actual venue resolutions for open positions.

 For each open position, map the ledger market to its venue slug via
 WATCHLIST.json and check the venue. RESOLVED markets auto-settle through
 cmd_settle's immutable path — same writer, same receipts, same
 verification (no second settlement mechanism). OPEN markets are skipped.
 AMBIGUOUS/ERROR go to hidden_files/resolution_review.jsonl, never
 auto-settled. The .us venue has no verified resolution endpoint, so .us
 markets always queue for review. --dry-run reports without writing.
 Settle stays live under kill (this only closes exposure), so this
 subcommand is ungated like settle.
 """
    entries = load_ledger()
    opens = open_positions(entries)
    if not opens:
        print("resolve-sweep: no open positions")
        return 0
    try:
        wl = json.load(open(WATCHLIST_PATH))["markets"]
    except (OSError, json.JSONDecodeError, KeyError) as ex:
        print(f"resolve-sweep refused: WATCHLIST unreadable ({ex})",
              file=sys.stderr)
        return 1
    settled_n = skipped_n = review_n = 0
    # WATCHLIST is keyed by short key but ledger rows carry the venue slug
    # (: the direct wl.get(m) lookup never matched slug-keyed
    # markets, so the sweep review-queued every open market with the
    # misleading "no WATCHLIST entry" reason instead of the correct
    # venue-based reason — the 10-01 "settle today" never executed).
    slug_to_meta = {v["slug"]: v for v in wl.values()
                    if isinstance(v, dict) and v.get("slug")}
    for m in sorted({e["market"] for e in opens}):
        if m in settled_markets():
            continue  # already recorded — immutable, never re-touched
        meta = slug_to_meta.get(m) or wl.get(m)
        if not meta:
            _resolve_review(m, "no WATCHLIST entry — cannot map to venue slug")
            review_n += 1
            continue
        venue, slug = meta.get("venue"), meta.get("slug")
        if venue == "us":
            _resolve_review(m, f"us venue ({slug}): no verified resolution "
                               "endpoint — human review required")
            review_n += 1
            continue
        if venue != "com" or not slug:
            _resolve_review(m, f"unknown venue mapping "
                               f"(venue={venue} slug={slug})")
            review_n += 1
            continue
        status, yes_won, evidence = classify_gamma_resolution(
            fetch_gamma_market(slug))
        if status == "OPEN":
            skipped_n += 1
            continue
        if status != "RESOLVED":
            _resolve_review(m, f"gamma: {status} — {evidence}")
            review_n += 1
            continue
        outcome = "YES" if yes_won else "NO"
        if a.dry_run:
            print(f"  would settle {m} -> {outcome} ({evidence})")
            settled_n += 1
            continue
        ns = argparse.Namespace(outcome=outcome, market=m, pnl=None,
                                resolved_cdt="", evidence="auto: " + evidence,
                                note="resolve-sweep auto-settle")
        code = cmd_settle(ns)
        if code == 0:
            settled_n += 1
            print(f"  auto-settled {m} -> {outcome}")
        else:
            _resolve_review(m, f"cmd_settle refused (exit {code})")
            review_n += 1
    print(f"resolve-sweep: {settled_n} settled, {skipped_n} still open, "
          f"{review_n} queued for review")
    return 0


def cmd_settle(a):
    outcome = normalize_outcome(a.outcome)
    if outcome is None:
        return fail(f"outcome must be YES|NO (got {a.outcome!r})")
    market = a.market.strip()
    if not market:
        return fail("market slug is required")

    # ---- validate everything BEFORE any write (atomicity: all-or-nothing
    # intent; writes below are ordered ledger -> settled.json -> dependents,
    # then verified — a crash mid-write is recoverable by re-running settle,
    # which completes the missing pieces) ----
    doc = load_json_doc(SETTLED_PATH, {})
    settled_entry = (doc.get("settled") or {}).get(market)
    entries = load_ledger()
    targets = [e for e in open_positions(entries) if e.get("market") == market]
    if settled_entry is not None:
        # Ghost-state completion (the operator's ruling #2 — terminal
        # closure): settled.json recorded this market's resolution, but the
        # ledger rows were never closed — the old settled.json exclusion
        # filter hid them instead of settling them. This is NOT a
        # re-settlement: settled.json is untouched and immutable (the recorded
        # outcome is reused, never re-argued); only the ledger-side closure is
        # completed — settle receipts, terminal row closure, brier
        # filing, worker_state/watchlist cleanup — so the ledger reads
        # absolute reality at rest.
        if not targets:
            return fail(f"{market} already in settled.json — settled markets "
                        "are immutable, never re-settled")
        outcome = "YES" if settled_entry.get("yes_won") else "NO"
        pnls = [(round(realized_pnl(e["side"], e["price_c"], e["size_usd"],
                              outcome) - (e.get("fee_usd", 0.0) or 0.0), 2),
                 "computed") for e in targets]
        return settle_finish(
            market, outcome, targets, pnls,
            stamp_short=settled_entry.get("resolved_cdt") or "",
            disp_short="CDT",
            evidence=("ledger-completion for pre-existing settled.json entry "
                      "(ghost-state repair)"),
            note=a.note or "", write_settled_json=False)
    if a.pnl is not None and len(targets) != 1:
        return fail(f"--pnl override needs exactly one open receipt "
                    f"({len(targets)} open on {market}) — omit to auto-compute")
    if a.resolved_cdt:
        stamp_short = a.resolved_cdt.strip()
        try:
            rdt = datetime.strptime(stamp_short, "%Y-%m-%d %H:%M")
            stamp_short = rdt.strftime("%Y-%m-%d %H:%M")
            # naive parse -> system timestamps are always CDT
            disp_short = rdt.strftime("%H:%M") + " CDT"
        except ValueError:
            return fail('--resolved-cdt must look like "2026-09-25 11:00"')
    else:
        rdt = now_cdt()
        stamp_short = rdt.strftime("%Y-%m-%d %H:%M")
        disp_short = rdt.strftime("%H:%M %Z")
    pnls = []
    for e in targets:
        if a.pnl is not None:
            pnls.append((round(a.pnl, 2), "override"))
        else:
            pnls.append((round(realized_pnl(e["side"], e["price_c"],
                                     e["size_usd"], outcome)
                              - (e.get("fee_usd", 0.0) or 0.0), 2), "computed"))

    # ---- write (normal path: records the resolution in settled.json) ----
    return settle_finish(market, outcome, targets, pnls, stamp_short,
                         disp_short, a.evidence or "", a.note or "",
                         write_settled_json=True)


def settle_finish(market, outcome, targets, pnls, stamp_short, disp_short,
                  evidence, note, write_settled_json):
    """Shared write+verify tail for both settle paths (normal + ghost-state
 completion). Write order: ledger (settle receipts + terminal row closure)
 -> settled.json (normal path only) -> brier shadow -> worker_state ->
 WATCHLIST -> STATUS.md, then verify. Re-running completes
 missing pieces; settled.json entries are never duplicated.

 PAPER.md is deliberately NOT written here (the operator's ruling
 #3): the JSON ledger is the singular source of truth and PAPER.md is a
 deterministic projection built by build_paper_view.py, run as the hourly
 worker's final step. book_trade.py never mutates Markdown."""
    stamp = now_cdt().isoformat()
    settle_write_ledger(targets, outcome, pnls, note)
    rows = {e["receipt_id"]: {"desk": e["desk"], "side": e["side"],
                             "entry_c": e["price_c"],
                             "pnl_usd": pnl}
            for e, (pnl, _m) in zip(targets, pnls)}
    if write_settled_json:
        settle_write_settled_json(market, outcome, stamp_short, evidence,
                                  rows)
    n_shadow = settle_write_brier_shadow(market, targets, stamp)
    removed_ws = settle_write_worker_state(targets)
    touched_wl = settle_write_watchlist(market, outcome, disp_short)
    status_ok, status_msg = settle_write_status(removed_ws)

    # ---- verify ----
    issues = verify_settle(market, [e["receipt_id"] for e in targets])
    if not touched_wl:
        print(f"WARN: no WATCHLIST market with slug {market} carried a "
              "position field — nothing removed there")
    if not status_ok:
        print(f"WARN: STATUS.md not patched ({status_msg}) — next hourly "
              "render regenerates it")
    if issues:
        print("SETTLE INCOMPLETE:")
        for i in issues:
            print("  " + i)
        return 1
    total = sum(p for p, _m in pnls)
    print(f"SETTLED {market} -> {outcome} | {len(targets)} receipt(s) | "
          f"realized ${total:+.2f} | shadow+{n_shadow} | "
          f"ws-{len(removed_ws)} wl-{len(touched_wl)}")
    return 0


def cmd_ledger(_a):
    for e in open_positions(load_ledger()):
        print(f"{e['receipt_id']} | {e['desk']:>2} | {e['side']:>3} | "
              f"{e['market'][:44]:<44} @ {e['price_c']:>6}c | ${e['size_usd']:>7.2f} "
              f"| fam={e.get('family_derived','')}"
              + (" | DIRECTIVE" if e.get("directive") else "")
              + (f" | shadows {e['shadow_of']}" if e.get("shadow_of") else ""))


def cmd_set_display(a):
    """Patch display fields on a book row (ruling #3).

 The PAPER.md projection is generated; these fields are the sanctioned
 repair path when the projection fails loudly on a missing thesis/ev_gate,
 or when a row's Notes need a timestamped annotation. Metadata only —
 never changes status, prices, or P&L.
 """
    entries = load_ledger()
    target = next((e for e in entries
                   if e.get("action") == "book"
                   and e.get("receipt_id") == a.receipt), None)
    if target is None:
        return fail(f"set-display: no book row {a.receipt}")
    patch = {}
    if a.thesis is not None:
        patch["thesis"] = a.thesis.strip()
    if a.ev_gate is not None:
        if a.ev_gate not in ("originated", "near-gate"):
            return fail("set-display: --ev-gate must be originated|near-gate")
        if target.get("desk") == "X" or target.get("directive"):
            return fail("set-display: ev_gate is derived for X/directives")
        patch["ev_gate"] = a.ev_gate
    if a.exit_note is not None:
        patch["exit_note"] = a.exit_note.strip()
    if a.market_display is not None:
        patch["market_display"] = a.market_display.strip()
    if a.notes is not None:
        patch["notes_display"] = a.notes.strip()
    if a.notes_append is not None:
        cur = (target.get("notes_display") or target.get("note") or "").strip()
        add = a.notes_append.strip()
        patch["notes_display"] = (cur + " " + add).strip() if cur else add
    if not patch:
        return fail("set-display: nothing to set")
    ledger_append_and_close([], {}, {a.receipt: patch})
    print(f"SET-DISPLAY OK {a.receipt}: {', '.join(sorted(patch))}")
    return 0


def cmd_audit(_a):
    entries = load_ledger()
    opens = open_positions(entries)
    issues = []
    # WATCHLIST key -> market slug crosswalk: bootstrap-era ledger rows
    # carry slugs while worker_state carries watchlist keys.
    slug_of = {}
    try:
        wl = json.load(open(os.path.join(ROOT, "desks", "WATCHLIST.json")))
        mkts = wl.get("markets", {})
        if isinstance(mkts, dict):
            for k, m in mkts.items():
                if isinstance(m, dict) and m.get("slug"):
                    slug_of[k] = m["slug"]
    except Exception:
        pass
    def ws_market_ids(p, k):
        return {k, slug_of.get(k)}
    try:
        ws = json.load(open(WS_PATH))
        ws_pos = ws.get("positions", {})
        if isinstance(ws_pos, list):
            # Skill-mandated worker_state schema (SKILL.md §7) writes
            # positions as a list keyed by market; index it by market key
            # for reconciliation. Exact receipt_id match is unavailable in
            # this form -> the desk+side+entry fallback below applies,
            # failing closed on ambiguity. (A previous fix stopped the
            # audit crashing here with AttributeError.)
            idx = {}
            for p in ws_pos:
                k = p.get("market") or p.get("key")
                if k:
                    idx.setdefault(k, p)
            ws_pos = idx
    except Exception as ex:
        print(f"worker_state unreadable: {ex}")
        ws_pos = {}
    for key, p in ws_pos.items():
        desk, side = p.get("desk"), p.get("side")
        entry = ws_entry_dollars(p)
        if desk == "X":
            continue  # X shadows tracked separately
        # Exact receipt_id match first: worker_state keys are receipt_ids
        # for every position the scripted booking paths created.
        match = [e for e in opens if e["receipt_id"] == key]
        if not match:
            # Market-identity match: watchlist key or its slug (bootstrap
            # rows carry slugs). Desk+side+side-aware-entry must also agree;
            # exact market identity resolves same-price twins.
            ids = ws_market_ids(p, key)
            match = [e for e in opens
                     if e["market"] in ids
                     and e["desk"] == desk and e["side"] == side.lower()
                     and ws_entry_side_close_enough(p, side, e["price_c"])]
        if not match:
            # Legacy fallback: worker_state positions predate the entry
            # field; entry=None means reconcile on desk+side only (weaker).
            # Side-aware variant compares the booked side's price against
            # the ws side-native entry (entry_no_c / entry_yes_c).
            # Ambiguous fallback matches FAIL CLOSED — they are reported,
            # never silently accepted.
            match = [e for e in opens
                     if e["desk"] == desk and e["side"] == side.lower()
                     and ws_entry_side_close_enough(p, side, e["price_c"])]
        if not match:
            issues.append(f"ORPHAN: worker_state '{key}' ({desk} {side} @ {entry}) "
                          f"has no ledger receipt — hand-written booking?")
        elif len(match) > 1:
            issues.append(f"AMBIGUOUS: worker_state '{key}' ({desk} {side} @ {entry}) "
                          f"matches {len(match)} ledger rows "
                          f"{[e['receipt_id'] for e in match]} — "
                          f"reconcile by receipt_id, not desk+side")
    for e in opens:
        if e["desk"] == "X":
            continue
        claims = [k for k in ws_pos if k == e["receipt_id"]]
        if not claims:
            # Market-identity claim: ws market key or its slug equals the
            # ledger row's market. Desk+side+side-aware-entry must agree.
            claims = [k for k, p in ws_pos.items()
                      if e["market"] in ws_market_ids(p, k)
                      and p.get("desk") == e["desk"]
                      and str(p.get("side", "")).lower() == e["side"]
                      and ws_entry_side_close_enough(p, e["side"], e["price_c"])]
        if not claims:
            claims = [k for k, p in ws_pos.items()
                      if p.get("desk") == e["desk"]
                      and str(p.get("side", "")).lower() == e["side"]
                      and ws_entry_side_close_enough(p, e["side"], e["price_c"])]
        if not claims:
            issues.append(f"UNMIRRORED: ledger {e['receipt_id']} ({e['desk']} {e['market']}) "
                          f"not in worker_state — ledger/state drift")
        elif len(claims) > 1:
            issues.append(f"AMBIGUOUS: ledger {e['receipt_id']} ({e['desk']} {e['market']}) "
                          f"claimed by {len(claims)} worker_state keys {claims} — "
                          f"duplicate assignment, reconcile by receipt_id")
    # X-shadow orphan check (R doctrine-hunt #3 backstop): every
    # open X shadow carrying a shadow_of link must point at an OPEN
    # originator book row. The exit cascade closes shadows with their
    # originator; this catches anything that slipped through (pre-cascade
    # exits, market-mismatch skips). Legacy backfill shadows with
    # shadow_of=None are grandfathered — no link, nothing to check.
    for e in opens:
        if e.get("desk") != "X" or not e.get("shadow_of"):
            continue
        src = next((o for o in opens
                    if o["receipt_id"] == e["shadow_of"]), None)
        if src is None:
            issues.append(f"ORPHAN: X shadow {e['receipt_id']} "
                          f"({e['market']}) shadows {e['shadow_of']}, "
                          f"which is not open — originator closed without "
                          f"cascade; exit the shadow by hand")
    if issues:
        print("AUDIT FAIL:")
        for i in issues:
            print("  " + i)
        return 1
    print(f"AUDIT OK: {len(opens)} open ledger positions reconcile with worker_state")
    return 0


def cmd_bootstrap(_a):
    if os.path.isfile(LEDGER):
        return fail("ledger exists — bootstrap is one-time only")
    try:
        ws = json.load(open(WS_PATH))
    except Exception as ex:
        return fail(f"worker_state unreadable: {ex}")
    seed = [
        # (ws_key, market_slug, family_declared, directive)
        ("c-btc80k-sep25-no", "bitcoin-above-80k-on-september-25-2026", "btc-80k-sep25", False),
        ("c-fed-hike-2026-no", "another-fed-rate-hike-in-2026", "fed-hike-2026", False),
        ("f-anthropic-no", "ipcc-anthropic-2026-09-30", "anthropic-ipo", True),
        ("f-btc-no-150k", "cpc-btc-150k-09-30-2026", "btc-150k", True),
        ("f-btc90k", "sept-btc-reach-90000", "btc-90k-sep", False),
        ("f-hormuz-traffic-no", "strait-of-hormuz-traffic-returns-to-normal-by-december-31",
         "hormuz-normalization", False),
        ("f-iran-ceasefire-no", "us-x-iran-ceasefire-continues-through-september-30-20260917",
         "iran-ceasefire-sep30", False),
        ("s-iran-ceasefire-no", "us-x-iran-ceasefire-continues-through-september-30-20260917",
         "iran-ceasefire-sep30", False),
    ]
    n = 0
    for key, slug, fam, directive in seed:
        p = ws["positions"].get(key)
        if not p:
            print(f"  skip {key}: not in worker_state")
            continue
        side = p["side"].lower()
        price_c = round(p["entry"] * 100, 2)
        size = {"C": 1.0, "F": 1.0, "S": 10.0}.get(p["desk"], 1.0)
        rec = {"action": "book", "receipt_id": f"bk-bootstrap-{n+1:02d}",
               "ts_cdt": "2026-09-24T22:15:00-05:00", "desk": p["desk"],
               "market": slug, "side": side, "price_c": price_c,
               "p_yes": None, "size_usd": size, "family_declared": fam,
               "family_derived": derive_family(slug), "directive": directive,
               "status": "open", "note": f"bootstrapped from worker_state '{key}'"}
        append(rec)
        n += 1
    print(f"bootstrapped {n} open positions into {LEDGER}")
    return 0


def fail(msg, ctx=None):
    # Proposer contract: rejections are LOGGED, never silently
    # clipped. A learner that can't see its rejections can't improve.
    # ctx = {"action","desk","market","proposer_id"} supplied by cmd_book.
    if ctx:
        try:
            with open(REJECTIONS, "a") as f:
                f.write(json.dumps({"ts_cdt": now_cdt().isoformat(),
                                    "action": ctx.get("action", ""),
                                    "desk": ctx.get("desk", ""),
                                    "market": ctx.get("market", ""),
                                    "proposer_id": ctx.get("proposer_id", ""),
                                    "reason": msg}) + "\n")
        except OSError:
            pass  # logging must never break the reject path itself
    print(f"REJECT: {msg}")
    return 3


def main():
    ap = argparse.ArgumentParser(description="Nightwatch booking gate — code, not prose")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("book")
    b.add_argument("--desk", choices=list(DESKS), required=True)
    b.add_argument("--market", required=True)
    b.add_argument("--side", choices=["yes", "no"], required=True)
    b.add_argument("--price", type=float, required=True,
                   help="price in CENTS, e.g. 87 = 87c (dollars are rejected by the unit tripwire)")
    b.add_argument("--p", type=float, required=True, help="P(Yes resolves true)")
    b.add_argument("--family", required=True)
    # Driver-concentration gate: macro driver from the framework-owned
    # taxonomy. Required on every booking; the cap is ABSOLUTE — directives
    # declare for tagging but are NOT exempt. Unknown keys REJECT.
    b.add_argument("--driver", default="",
                   help="macro driver, e.g. iran-geopolitics (required; see "
                        "hidden_files/driver_taxonomy.json)")
    # Mikiri thesis schema (D-003): the named loser and the
    # initiative tag. Required on every booking (directives declare for
    # tagging); validated in code so failures REJECT through the logged path.
    b.add_argument("--loser", default="",
                   help="who is wrong on the other side and why (required)")
    b.add_argument("--sen", default="",
                   help="initiative: ken_no_sen | tai_no_sen | tai_tai_no_sen "
                        "(required)")
    b.add_argument("--directive", action="store_true")
    b.add_argument("--note", default="")
    # Display fields for the PAPER.md projection (ruling #3):
    # the 1-line thesis and the EV-gate label. The projection FAILS LOUDLY
    # on rows missing them — pass them at booking time, don't hand-edit.
    b.add_argument("--thesis", default="",
                   help="1-line thesis for the PAPER.md Ledger projection")
    b.add_argument("--ev-gate", default="", choices=["", "originated", "near-gate"],
                   help="EV gate label: originated | near-gate (X and "
                        "directives derive their label)")
    b.add_argument("--trap-id", default="",
                   help="D-004: id of the pre-registered trap this booking "
                        "executes (90s hook tripwire). Recorded on the "
                        "receipt for trap audit; the booking passes through "
                        "every gate identically — a trap authorizes the "
                        "attempt, never the outcome.")
    # ML instrumentation: funnel event slug (or one of its market
    # slugs) when the thesis originated from a funnel candidate. Used only to
    # snapshot decision-time features into decision_features.jsonl for future
    # calibration/proposer training — never affects the booking.
    b.add_argument("--funnel-event", default="",
                   help="funnel candidate event slug this thesis came from "
                        "(optional; enables decision-feature logging)")
    b.add_argument("--nominate-real", action="store_true")
    b.add_argument("--r-rating", choices=["HARD", "SOFT", "MISS"], default=None)
    # Proposer contract: a learned/statistical proposer may advise
    # a booking, but size_suggestion is advisory only — the script computes the
    # Kelly size and the suggestion is logged for scoring, never executed.
    b.add_argument("--proposer", default="",
                   help="proposer id, e.g. bandit-v0 (advisory only)")
    b.add_argument("--size-suggest", type=float, default=None,
                   help="proposer's suggested USD size (logged, never executed)")
    b.add_argument("--confirm-cents", action="store_true",
                   help="explicitly assert --price is in CENTS: clears the "
                        "no-poller-quote and unit-ambiguity rejections, never "
                        "the 100x dollars-confusion tripwire")

    s = sub.add_parser("shadow")
    s.add_argument("--market", required=True)
    s.add_argument("--side", choices=["yes", "no"], required=True)
    s.add_argument("--price", type=float, required=True,
                   help="price in CENTS, e.g. 87 = 87c")
    s.add_argument("--shadow-of", required=True)
    s.add_argument("--attempted", type=float, required=True,
                   help="requested USD; the fill engine depth-caps the actual fill")
    s.add_argument("--note", default="")
    # Display field for the PAPER.md projection (ruling #3): the 1-line
    # thesis. X's EV-gate label derives as "sandbox".
    s.add_argument("--thesis", default="",
                   help="1-line thesis for the PAPER.md Ledger projection")
    s.add_argument("--confirm-cents", action="store_true",
                   help="explicitly assert --price is in CENTS (see book)")

    e = sub.add_parser("exit")
    e.add_argument("--receipt", required=True)
    e.add_argument("--exit-price", type=float, default=None,
                   help="exit price in CENTS, e.g. 80 = 80c")
    e.add_argument("--auto-price", action="store_true",
                   help="price the exit off the poller cache instead of a "
                        "manual --exit-price (the stream-outage lifeboat: "
                        "coarse 90s data, tagged on the receipt)")
    e.add_argument("--confirm-cents", action="store_true",
                   help="explicitly assert --exit-price is in CENTS (see book)")
    e.add_argument("--note", default="")

    st = sub.add_parser("settle")
    st.add_argument("--market", required=True,
                    help="ledger market slug (= settled.json key)")
    st.add_argument("--outcome", required=True,
                    help="YES|NO (yes/no/y/n/1/0 accepted)")
    st.add_argument("--pnl", type=float, default=None,
                    help="override realized P&L in USD (single-receipt only; "
                         "otherwise computed from the receipt)")
    st.add_argument("--evidence", default="",
                    help="one-line resolution evidence for settled.json")
    st.add_argument("--resolved-cdt", default="",
                    help='resolution timestamp "YYYY-MM-DD HH:MM"; default now')
    st.add_argument("--note", default="")

    # Display-field repair (ruling #3): the sanctioned path for
    # fixing a projection FAIL on missing thesis/ev_gate, or annotating a
    # row's Notes. Metadata only — never touches status/prices/P&L.
    sd = sub.add_parser("set-display")
    sd.add_argument("--receipt", required=True)
    sd.add_argument("--thesis", default=None)
    sd.add_argument("--ev-gate", default=None,
                    choices=["originated", "near-gate"])
    sd.add_argument("--exit-note", default=None)
    sd.add_argument("--market-display", default=None)
    sd.add_argument("--notes", default=None,
                    help="replace the Notes cell")
    sd.add_argument("--notes-append", default=None,
                    help="append to the Notes cell (timestamped annotations)")

    sub.add_parser("audit")
    sub.add_parser("ledger")
    sub.add_parser("bootstrap")
    k = sub.add_parser("kill")
    k.add_argument("--reason", default="")
    sub.add_parser("resume")
    rs = sub.add_parser("resolve-sweep")
    rs.add_argument("--dry-run", action="store_true",
                    help="report what would settle without writing")

    a = ap.parse_args()
    # Kill semantic: NO NEW RISK. book/shadow/bootstrap are blocked while the
    # flag exists. `exit` and `settle` deliberately stay live — like exit,
    # settle only closes already-open exposure and records an external event
    # (resolution already happened); a kill switch must never be the thing
    # keeping a dead position on the books.
    # The doctrine trip (hidden_files/doctrine.trip, written ONLY by
    # bin/trip_doctrines.py on kill-class proposals for D-001/D-003/D-004,
    # cleared ONLY by the framework/the operator) severs new risk through this SAME path —
    # one condition, same exit 4, no second mechanism.
    # The stream watchdog (Phase 2.1) adds two more conditions, same path:
    # Layer 1 = the supervisor daemon's stream_health.trip file (fast,
    # continuous); Layer 2 = the executor's own local derivation from the
    # snapshot seq counter (trust-no-one backstop). Either trips -> exit 4.
    # A trip file from a dead supervisor is disregarded: the executor falls
    # back to pure local derivation (who watches the watcher: staleness).
    if a.cmd in ("book", "shadow", "bootstrap"):
        flag = kill_engaged()
        if flag:
            print(f"KILL SWITCH ENGAGED ({flag}) — new risk blocked: {a.cmd}",
                  file=sys.stderr)
            return 4
        trip = doctrine_tripped()
        if trip:
            print(f"DOCTRINE TRIP ENGAGED ({trip}) — new risk blocked: {a.cmd}",
                  file=sys.stderr)
            return 4
        if stream_watch is not None:
            sw_tripped, sw_reason = stream_watch.supervisor_verdict()
            if sw_tripped:
                print(f"STREAM WATCHDOG TRIP ({sw_reason}) — new risk "
                      f"blocked: {a.cmd}", file=sys.stderr)
                return 4
            if sw_reason and sw_reason.startswith(
                    "supervisor_stale_disregarded"):
                print(f"STREAM WATCHDOG NOTICE ({sw_reason}) — supervisor "
                      f"dead, deciding locally", file=sys.stderr)
            sw_local = stream_watch.local_watchdog()
            if sw_local:
                print(f"STREAM STALL DERIVED LOCALLY ({sw_local}) — new risk "
                      f"blocked: {a.cmd}", file=sys.stderr)
                return 4
        dh = data_health()
        if dh:
            print(f"DATA HEALTH RED ({dh}) — new risk blocked: {a.cmd}",
                  file=sys.stderr)
            return 4
        # Provenance isolation (reform 4): local-tier output carries an
        # immutable tag (bin/provenance.py). A tagged payload attempting the
        # real-money `book` path is refused mechanically — exit 4, same as
        # the kill switch — without human intervention. Paper `shadow`
        # remains eligible: local -> paper freely, local -> money never.
        # Refusal-only (no auto-arm of kill.switch): a false positive must
        # not DoS the whole booking path; blocks are logged + alertable.
        if a.cmd == "book":
            if provenance is None:
                print("PROVENANCE DETECTION OFFLINE (module missing) — "
                      "local-tier check skipped", file=sys.stderr)
            else:
                str_fields = [v for v in vars(a).values()
                              if isinstance(v, str)]
                if provenance.should_refuse(a.cmd, *str_fields):
                    _log_provenance_block(a.cmd, str_fields)
                    print("LOCAL-PROVENANCE BLOCK — local-tier output "
                          f"refused on real-money path: {a.cmd} (exit 4)",
                          file=sys.stderr)
                    return 4
    code = {"book": cmd_book, "shadow": cmd_shadow, "exit": cmd_exit,
            "settle": cmd_settle, "resolve-sweep": cmd_resolve_sweep,
            "audit": cmd_audit, "ledger": cmd_ledger,
            "set-display": cmd_set_display,
            "bootstrap": cmd_bootstrap, "kill": cmd_kill,
            "resume": cmd_resume}[a.cmd](a)
    sys.exit(code)


if __name__ == "__main__":
    sys.exit(main())
