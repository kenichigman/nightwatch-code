#!/usr/bin/env python3
"""fill_engine.py — honest paper fills for Nightwatch.

Replaces the fixed 0.5c adverse-slippage haircut (worker-applied prose) with a
mechanical book walk in the booking path — code over prose, per the enforcement
hierarchy (the reviewer's ordered plan, the operator approved "breadth first"):

 1. Fill against the actual order book at booking time, so slippage grows
 with size BY CONSTRUCTION. A $1 fill and a $20k fill no longer get the
 same 0.5c haircut.
 2. Taker fees modeled per the venue's published schedule (recheck date
 below). Every paper trade was previously flattered by ~1-3%.
 3. Each clip capped by the depth the book absorbs within 1c of the touch —
 not by share of daily volume. Volume says how much trades in a day, not
 how much you can take at one moment.
 4. X becomes the breadth desk: many small depth-capped clips, more markets,
 more resolutions per week (resolutions are the scarce input).
 5. Capacity revisited later as a pre-registered experiment on whatever desk
 shows an edge, with this walk already in place.

This module is pure (no I/O, no network): levels in, fill math out. The
booking path (book_trade.py) fetches the snapshot and calls in. Tests live in
bin/test_fill_engine.py.

Fee schedule (Polymarket International / .com), verified against
three agreeing third-party guides (launchpoly, polymart, marketmath):
 fee_usd = shares * fee_rate * p * (1 - p), p in 0..1
Category taker rates: crypto 0.07 | sports 0.05 | economics/culture/weather/
other/general 0.05 | finance/politics/tech/mentions 0.04 | geopolitics/world 0.
Makers pay 0 and earn a rebate (paper fills are always taker-style, so the
rebate never applies here). Sell-side ambiguity: one guide says sells are not
charged, another says they are — we CHARGE on both sides (conservative: it can
only understate edge, never flatter it) and note it here.

Polymarket US (.us): taker theta 0.0695 since per skinbethub
(ats.io reported 0.06 pre-October — conflict noted, newer source wins).
Same p*(1-p) curve shape.

FEE_SCHEDULE_RECHECK = "": the venue changes this; re-verify then.
"""

FEE_SCHEDULE_RECHECK = "2027-01-04"

# .com international taker rates by category tag (lowercase).
FEE_RATES_COM = {
    "crypto": 0.07,
    "sports": 0.05,
    "economics": 0.05,
    "culture": 0.05,
    "weather": 0.05,
    "other": 0.05,
    "general": 0.05,
    "finance": 0.04,
    "politics": 0.04,
    "tech": 0.04,
    "technology": 0.04,
    "mentions": 0.04,
    # Fee-free by venue policy — explicit zero, NOT unknown.
    "geopolitics": 0.0,
    "world": 0.0,
    "world events": 0.0,
}

# Polymarket US taker theta (same curve). See module docstring for sourcing.
FEE_RATE_US = 0.0695

# Depth tolerance: a clip is capped at what the book absorbs within this of
# the touch. (the reviewer's plan: "the size the book absorbs within about 1c".)
DEPTH_TOL_CENTS = 1.0

# Minimum honest fill. Below this the book is dead for our purposes — refuse
# rather than book dust at a fantasy price.
MIN_FILL_USD = 0.10


def taker_fee_usd(shares, price01, fee_rate):
    """Venue taker fee in USD. price01 in 0..1."""
    if shares <= 0 or fee_rate <= 0 or not (0 < price01 < 1):
        return 0.0
    return shares * fee_rate * price01 * (1.0 - price01)


def category_fee_rate(tags):
    """Map gamma tags to a .com taker rate.

 tags: iterable of str or dicts with label/slug keys (gamma shape varies).
 Returns (rate, unknown, matched_tag). Unknown categories get rate 0.0 AND
 unknown=True so the ledger logs the fee as explicitly-zero, never
 silently-zero.
 """
    seen = []
    for t in tags or []:
        if isinstance(t, dict):
            for k in ("slug", "label", "name"):
                if t.get(k):
                    seen.append(str(t[k]).strip().lower())
        else:
            seen.append(str(t).strip().lower())
    for s in seen:
        if s in FEE_RATES_COM:
            return FEE_RATES_COM[s], False, s
    return 0.0, True, "unknown"


def normalize_levels(raw):
    """raw: list of [price, size] pairs or {'price':..,'size':..} dicts.
 Prices accepted in 0..1 dollars or 1..100 cents (magnitude-detected).
 Returns [(price01, size_shares)] sorted best-first (highest first — the
 caller reverses for asks). Garbage levels are dropped, never guessed.
 """
    out = []
    for lvl in raw or []:
        try:
            if isinstance(lvl, dict):
                p, s = float(lvl["price"]), float(lvl["size"])
            else:
                p, s = float(lvl[0]), float(lvl[1])
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        if s <= 0:
            continue
        if p > 1.5:  # cents
            p = p / 100.0
        if not (0 < p < 1):
            continue
        out.append((p, s))
    out.sort(key=lambda x: -x[0])
    return out


def walk_book(levels_asks_best_first, size_usd):
    """Walk the ask side (buys) for size_usd.

 levels: [(price01, size_shares)] sorted best ask first (lowest price).
 Returns dict(filled_usd, vwap01, shares, exhausted). filled_usd is the
 actual USD spent walking; unfilled = size_usd - filled_usd.
 """
    remaining = size_usd
    cost = 0.0
    shares = 0.0
    for price, avail in levels_asks_best_first:
        if remaining <= 1e-9:
            break
        take_usd = min(remaining, price * avail)
        take_shares = take_usd / price
        cost += take_usd
        shares += take_shares
        remaining -= take_usd
    vwap = (cost / shares) if shares > 0 else 0.0
    return {"filled_usd": round(cost, 2),
            "vwap01": vwap,
            "shares": shares,
            "exhausted": remaining > 1e-9}


def walk_book_sell(levels_bids_best_first, shares):
    """Walk the bid side (sells) for a share count. Mirror of walk_book."""
    remaining = shares
    proceeds = 0.0
    sold = 0.0
    for price, avail in levels_bids_best_first:
        if remaining <= 1e-9:
            break
        take_shares = min(remaining, avail)
        proceeds += take_shares * price
        sold += take_shares
        remaining -= take_shares
    vwap = (proceeds / sold) if sold > 0 else 0.0
    return {"proceeds_usd": round(proceeds, 2),
            "vwap01": vwap,
            "shares": sold,
            "exhausted": remaining > 1e-9}


def depth_within_cents(levels_best_first, touch01, tol_cents=DEPTH_TOL_CENTS):
    """USD the book absorbs at levels within tol_cents of the touch.

 This is the clip cap: volume-independent, moment-specific. A level counts
 only while its distance from the touch is within tolerance.
 """
    total = 0.0
    for price, size in levels_best_first:
        if abs(price - touch01) * 100.0 <= tol_cents + 1e-9:
            total += price * size
        else:
            break  # levels are price-ordered; beyond tolerance stays beyond
    return round(total, 2)
