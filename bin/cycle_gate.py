#!/usr/bin/env python3
"""cycle_gate.py — deterministic FULL/LIGHT/KILL verdict for the hourly brain.

The runner fan-out is the cycle's dominant cost; on truly quiet hours it buys
nothing (observed: full cycles returning 20 evaluated / 0 trades / 20 passes).
This script computes the gate from disk state alone — no LLM judgment — so the
cron body can route BEFORE the worker reads the 30KB skill file:

  KILL  -> kill.switch or doctrine.trip present: exits-only kill mode.
  LIGHT -> all quiet: hook live, no wake in 65m, no position within 3c of warn,
           r_pending empty, no pending key request, hook not blind.
  FULL  -> anything else (names the failed gate).

Reads: hook log, hook price cache, worker_state.json, market_meta.json,
       real_money_request.json, kill.switch / doctrine.trip.
SCHEMA NOTES (verify against sources before changing these reads; 2026-09-26 EVENT):
- market_meta.json = {"_comment": str, "markets": {hook_key: {slug, resolves, ...}}} — unwrap "markets".
- worker_state.json positions = {bid: {market, side, entry_c, adverse_c, px_held, desk}} — entry_c, NOT "entry".
- hook nightwatch-prices.json px is the YES-side price: held_px = px (yes) else 1-px (no).
Prints JSON to stdout; exit 0 always (a gate never fails loudly — on any read
error it degrades to FULL with the error as the reason).
Convention: the main agent deletes hidden_files/real_money_request.json after
handling a key request; its presence means a nomination is still pending.
"""
import json, os, sys, time
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIDDEN = os.path.join(ROOT, "hidden_files")
HOOK_LOG = os.path.expanduser("~/hooks/logs/nightwatch-price-watch.jsonl")
HOOK_PRICES = os.path.expanduser("~/hooks/state/nightwatch-prices.json")
CDT = timezone(timedelta(hours=-5))

WARN_C = 0.05          # ~5c mechanical warn threshold
GATE_C = WARN_C - 0.03 # within 3c of warn -> FULL
HOOK_STALE_S = 600     # no tick in 10 min -> hook may be down -> FULL
WAKE_WINDOW_S = 65 * 60
FAIL_BLIND_FRAC = 0.5  # >50% failed ticks in window -> FULL (flying blind)


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def main():
    now_ms = int(time.time() * 1000)
    reasons = []

    # 0. Kill switch / doctrine trip — bypasses everything.
    for name in ("kill.switch", "doctrine.trip"):
        if os.path.exists(os.path.join(HIDDEN, name)):
            return verdict("KILL", ["kill-file present: %s" % name], now_ms)

    # 1-2. Hook liveness + wake scan (tail only; ~90s ticks, 200 lines ~= 5h).
    ticks = []
    try:
        with open(HOOK_LOG) as f:
            lines = f.readlines()[-200:]
        for ln in lines:
            try:
                o = json.loads(ln)
                ticks.append((o.get("started_at_ms", 0), o.get("outcome", "")))
            except Exception:
                continue
    except Exception as e:
        return verdict("FULL", ["hook log unreadable: %s" % e], now_ms)
    if not ticks:
        return verdict("FULL", ["hook log empty"], now_ms)
    newest_age_s = (now_ms - max(t for t, _ in ticks)) / 1000
    if newest_age_s > HOOK_STALE_S:
        return verdict("FULL", ["hook stale: newest tick %.0fs ago" % newest_age_s], now_ms)
    window = [(t, o) for t, o in ticks if now_ms - t <= WAKE_WINDOW_S * 1000]
    wakes = sum(1 for _, o in window if o == "wake")
    if wakes:
        return verdict("FULL", ["hook wake x%d in last 65m" % wakes], now_ms)
    if window and sum(1 for _, o in window if o == "failed") / len(window) > FAIL_BLIND_FRAC:
        return verdict("FULL", ["hook blind: >50%% failed ticks in window"], now_ms)

    # 3. Positions within 3c of warn (adverse move vs entry, hook px).
    ws = load_json(os.path.join(HIDDEN, "worker_state.json"), {})
    meta = load_json(os.path.join(HIDDEN, "market_meta.json"), {})
    if isinstance(meta, dict) and isinstance(meta.get("markets"), dict):
        meta = meta["markets"]  # unwrap wrapper ({_comment, markets}) to key->meta-dict
    prices = load_json(HOOK_PRICES, {})
    slug_to_key = {}
    for key, m in (meta.items() if isinstance(meta, dict) else []):
        # 2026-09-27 23:50 CDT: index by the meta DICT KEY (the worker_state/hook id,
        # e.g. 'iran-ceasefire-sep30') as well as the "slug" field, which is the
        # Polymarket URL slug and never matches a position's market id.
        slug_to_key.setdefault(key, key)
        s = (m.get("slug") or "")
        if s:
            slug_to_key.setdefault(s, key)
    _pos = ws.get("positions") or {}
    if isinstance(_pos, dict):
        pos_iter = _pos.items()
    elif isinstance(_pos, list):
        # 2026-09-27 23:48 CDT: worker_state positions moved to a list schema:
        # [{market, desk, side ("Yes"/"No"), entry_yes_c/entry_no_c, adverse_c, state}].
        # Normalize to the {bid: {market, side, entry_c}} shape the check below wants.
        pos_iter = []
        for i, q in enumerate(_pos):
            if not isinstance(q, dict):
                return verdict("FULL", ["position #%d has bad schema" % i], now_ms)
            _norm = {
                "market": q.get("market", q.get("key", "")),
                "side": str(q.get("side", "")).lower(),
                "entry": q.get("entry"),
            }
            # 2026-10-04 21:48 CDT fix: only carry entry_c when a real value
            # is present. An unconditional "entry_c": None shadowed the
            # legacy "entry" fallback, so legacy-schema rows failed closed
            # as "bad schema" instead of being evaluated.
            _ec = q.get("entry_c", q.get("entry_yes_c", q.get("entry_no_c")))
            if _ec is not None:
                _norm["entry_c"] = _ec
            # 2026-10-07 17:48 CDT fix: the producer writes entry_yes_px /
            # entry_no_px (dollars) on every row (8/8 rows on 2026-10-07), and
            # the check below has a dedicated dollars branch for them — but the
            # normalization dropped the keys, so every row failed closed as
            # "bad schema" and every quiet hour forced FULL. Carry them through.
            for _pxk in ("entry_yes_px", "entry_no_px"):
                if isinstance(q.get(_pxk), (int, float)):
                    _norm[_pxk] = q[_pxk]
            pos_iter.append((
                # 2026-09-30 21:48 CDT fix: worker_state positions use "key", not
                # "market" — fall back to "key" or the empty slug suffix-matches
                # the first map key ("".startswith(s) is False but
                # s.startswith("") is True), pulling a wrong market's price and
                # fabricating adverse (phantom +97.5c forced a false FULL).
                "%s/%s" % (q.get("desk", "?"), q.get("market", q.get("key", "?"))),
                _norm,
            ))
    else:
        return verdict("FULL", ["positions has bad schema"], now_ms)
    for bid, p in pos_iter:
        if not isinstance(p, dict):
            return verdict("FULL", ["position %s has bad schema" % bid], now_ms)
        slug, side = p.get("market", bid), p.get("side")
        side = str(side).lower() if side is not None else side
        # entry_c is CENTS per the contract above (matches book_ledger price_c);
        # held_px is dollars. Convert before comparing. Legacy "entry" key was dollars.
        # 2026-09-28 04:48 CDT: worker_state dict-branch schema drifted to
        # {side: "Yes"/"No" (capitalized), entry_yes_px: dollars YES price} — normalize.
        # 2026-10-07 17:50 CDT fix: the condition checked `"entry" not in p`, but
        # the list normalization above ALWAYS sets the "entry" key (possibly None),
        # so the dollars branch could never fire for normalized rows. Test the value,
        # not the key's presence: absent key and None entry are equivalent here.
        if isinstance(p.get("entry_yes_px"), (int, float)) and "entry_c" not in p and p.get("entry") is None:
            ey = p["entry_yes_px"]
            entry_raw = ey if side == "yes" else 1.0 - ey  # position-side entry, dollars
        else:
            # 2026-09-28 21:58 CDT: worker_state dict-branch uses side-native
            # cents (entry_yes_c/entry_no_c); select by side, else fall back.
            cands = {"yes": p.get("entry_yes_c"), "no": p.get("entry_no_c")}
            side_c = cands.get(side) if side in cands else None
            if side_c is not None:
                entry_raw = side_c / 100.0  # *_c keys are cents; entry_raw is dollars
            else:
                entry_raw = p.get("entry_c", p.get("entry"))
        entry = (entry_raw / 100.0) if ("entry_c" in p and isinstance(entry_raw, (int, float))) else entry_raw
        if side not in ("yes", "no") or entry is None:
            return verdict("FULL", ["position %s has bad schema" % bid], now_ms)
        key = slug_to_key.get(slug)
        if key is None:  # suffix-tolerant match (slugs like ...-20260917)
            for s, k in slug_to_key.items():
                # 2026-09-30 21:48 CDT fix: never suffix-match an empty slug —
                # s.startswith("") is True for every key and would map to the
                # first key alphabetically (phantom adverse, see note above).
                if slug and (slug.startswith(s) or s.startswith(slug)):
                    key = k
                    break
        if key is None:
            m = meta.get(slug, {}) if isinstance(meta, dict) else {}
            res = m.get("resolves")
            try:
                resolved = bool(res and datetime.fromisoformat(res) < datetime.now(timezone.utc))
            except Exception:
                resolved = False
            if resolved:
                reasons.append("info: position %s market resolved, skipping" % bid)
                continue
            return verdict("FULL", ["position %s unpriced (no hook/market_meta mapping)" % bid], now_ms)
        px = (prices.get(key) or {}).get("px")
        if px is None:
            return verdict("FULL", ["position %s: no hook price for %s" % (bid, key)], now_ms)
        held_px = px if side == "yes" else 1.0 - px  # hook px is the YES price; held_px is the POSITION-side price
        # 2026-09-27 10:48 CDT correction: adverse = entry - held_px for BOTH sides
        # (positive = position lost value = against us). The 03:55 "sign fix" set the
        # no-branch to (held_px - entry), which reads a genuine loss as negative
        # "favorable" (e.g. F No@13 with no-px 5.5c -> -7.5c) and blinds check #3 to
        # no-side warn proximity. Matches the hook's own adverse field and the
        # 09:48 manager-note convention (adverse = Yes_now - Yes_entry on No legs).
        adverse = entry - held_px
        if adverse >= GATE_C:
            return verdict("FULL", ["position %s adverse %+.1fc (within 3c of warn)" % (bid, adverse * 100)], now_ms)

    # 4. R overdue / real-money nomination pending.
    if ws.get("r_pending"):
        return verdict("FULL", ["r_pending non-empty (%d)" % len(ws["r_pending"])], now_ms)
    if os.path.exists(os.path.join(HIDDEN, "real_money_request.json")):
        return verdict("FULL", ["real_money_request.json pending"], now_ms)

    return verdict("LIGHT", reasons, now_ms)


def verdict(v, reasons, now_ms):
    print(json.dumps({
        "verdict": v,
        "reasons": reasons,
        "checked_at_cdt": datetime.fromtimestamp(now_ms / 1000, CDT).strftime("%Y-%m-%d %H:%M:%S"),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
