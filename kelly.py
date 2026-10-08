#!/usr/bin/env python3
"""Nightwatch Kelly position sizer for binary (Polymarket) markets.

Fractional-Kelly sizing with the Nightwatch EV gate and guardrail overlay.
Personality shapes what each desk looks at — the math stays honest.

Usage:
    kelly.py --side yes --price 76 --p 0.85 --bankroll 500 [--fraction 0.25] [--cap 10]

Math (price c and probability p as decimals):
    Yes at c:  full Kelly fraction f* = (p - c) / (1 - c)
    No  at c:  full Kelly fraction f* = ((1 - p) - c) / (1 - c)

Gates enforced:
    - EV gate: edge |p - c| must exceed the 5pt probability-error band,
      i.e. EV stays positive across p +/- 5pts. Otherwise: NO BET.
    - Fractional Kelly (default 1/4): full Kelly assumes p is exact.
      Our p estimates are not exact, so we size at --fraction of f*.
    - --cap: book-level max per trade (M: $1, S: $10, F: $1).
    - Real-money overlay printed for reference: $1 initial max,
      $3 daily-loss cap, $5 balance hard stop, $3 max concurrent risk.
"""

import argparse
import sys

ERROR_BAND = 0.05  # five-point probability error


def kelly_fraction(side: str, c: float, p: float) -> float:
    if side == "yes":
        return (p - c) / (1 - c)
    return ((1 - p) - c) / (1 - c)


def main() -> int:
    ap = argparse.ArgumentParser(description="Nightwatch Kelly sizer for binary markets")
    ap.add_argument("--side", choices=["yes", "no"], required=True)
    ap.add_argument("--price", type=float, required=True, help="entry price in cents (0-100)")
    ap.add_argument("--p", type=float, required=True, help="estimated probability 0-1")
    ap.add_argument("--bankroll", type=float, required=True, help="book bankroll in $")
    ap.add_argument("--fraction", type=float, default=0.25, help="Kelly fraction (default 0.25)")
    ap.add_argument("--cap", type=float, default=None, help="max $ per trade for this book")
    a = ap.parse_args()

    c = a.price / 100.0
    if not (0 < c < 1) or not (0 < a.p < 1):
        print("price must be 0-100 (exclusive), p must be 0-1 (exclusive)")
        return 2

    win_p = a.p if a.side == "yes" else 1 - a.p
    edge = win_p - c  # edge in probability points vs price

    print(f"side={a.side} price={a.price:.1f}c  p={a.p:.3f}  bankroll=${a.bankroll:.2f}")
    print(f"edge vs price: {edge * 100:+.1f}pts", end="")

    if edge <= ERROR_BAND:
        print(f"  -> inside the {ERROR_BAND * 100:.0f}pt error band: NO BET (gate fails)")
        return 0
    print("  -> clears the error band")

    f_full = kelly_fraction(a.side, c, a.p)
    if f_full <= 0:
        print("Kelly fraction <= 0: NO BET")
        return 0
    f_frac = f_full * a.fraction
    size_full = f_full * a.bankroll
    size_frac = f_frac * a.bankroll

    print(f"full Kelly:    {f_full * 100:6.2f}%  = ${size_full:8.2f}")
    print(f"{a.fraction:g} Kelly:     {f_frac * 100:6.2f}%  = ${size_frac:8.2f}")

    sized = size_frac
    notes = []
    if a.cap is not None and sized > a.cap:
        notes.append(f"capped at book max ${a.cap:.2f}")
        sized = a.cap
    # Real-money overlay (informational — the gates decide, Kelly advises)
    if sized > 1.0:
        notes.append("real-money initial max is $1/trade ($2 only after 5 settled + positive P&L)")
    if notes:
        print("notes: " + "; ".join(notes))
    print(f"SUGGESTED SIZE: ${sized:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
