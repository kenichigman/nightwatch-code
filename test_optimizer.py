#!/usr/bin/env python3
"""test_optimizer.py — synthetic tests for the Phase 3.1 optimizer scaffold.

Strictly off-path: tests the pure function with synthetic inputs only.
No ledger, no production, no wiring. Run ONLY via run_tests.sh.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from optimizer import (
    MarketSnapshot, PortfolioPosition,
    kalman_update, huber_cap, optimize_portfolio,
)

failures = []


def check(name, cond, detail=""):
    print(("ok: " if cond else "FAIL: ") + name
          + (f" ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def snap(mid, price=0.5, vol=0.1, edge=0.05):
    return MarketSnapshot(market_id=mid, price=price,
                          volatility=vol, edge_obs=edge)


def test_kalman_fuses_prior_and_observation():
    # High observation noise -> posterior stays near prior
    m, _ = kalman_update(prior_mean=0.0, prior_var=0.01,
                         observation=1.0, obs_var=100.0, process_var=0.0)
    check("high obs noise -> near prior", abs(m) < 0.05, m)
    # High prior uncertainty -> posterior moves toward observation
    m, _ = kalman_update(prior_mean=0.0, prior_var=100.0,
                         observation=1.0, obs_var=0.01, process_var=0.0)
    check("high prior var -> near obs", abs(m - 1.0) < 0.05, m)
    # Posterior variance is bounded by both inputs
    _, v = kalman_update(0.0, 1.0, 0.5, 0.25, 0.01)
    check("posterior var positive and < prior+Q", 0 < v < 1.01, v)


def test_huber_caps_outliers():
    check("within band untouched", huber_cap(1.5, 2.0) == 1.5)
    check("positive capped", huber_cap(5.0, 2.0) == 2.0)
    check("negative capped", huber_cap(-5.0, 2.0) == -2.0)
    check("zero delta -> zero", huber_cap(5.0, 0.0) == 0.0)
    check("negative delta -> zero", huber_cap(5.0, -1.0) == 0.0)


def test_optimizer_deterministic_and_pure():
    snaps = [snap("a", edge=0.05), snap("b", edge=-0.03), snap("c", edge=0.0)]
    port = [PortfolioPosition("a", 1.0)]
    r1 = optimize_portfolio(snaps, port)
    r2 = optimize_portfolio(snaps, port)
    check("deterministic", r1 == r2)
    check("all markets present", set(r1) == {"a", "b", "c"})
    check("positive edge -> long", r1["a"] > 0, r1["a"])
    check("negative edge -> short", r1["b"] < 0, r1["b"])
    check("zero edge -> zero", r1["c"] == 0.0, r1["c"])


def test_l1_constraint():
    # Ten strong signals — unconstrained gross would exceed the limit
    snaps = [snap(f"m{i}", edge=0.2, vol=0.05) for i in range(10)]
    out = optimize_portfolio(snaps, [], l1_limit=5.0, max_position=3.0)
    gross = sum(abs(v) for v in out.values())
    check("gross <= l1_limit", gross <= 5.0 + 1e-9, gross)
    check("gross saturates limit (all same sign)", gross > 4.9, gross)
    # Zero limit -> all zero
    out0 = optimize_portfolio(snaps, [], l1_limit=0.0)
    check("zero limit -> all zero", all(v == 0.0 for v in out0.values()))


def test_volatility_scaling():
    # Same edge, different vol: lower vol -> larger position (Kelly)
    lo = optimize_portfolio([snap("x", edge=0.05, vol=0.05)], [])
    hi = optimize_portfolio([snap("x", edge=0.05, vol=0.20)], [])
    check("lower vol -> larger size", abs(lo["x"]) > abs(hi["x"]),
          f"{lo['x']} vs {hi['x']}")
    # Zero vol -> no position (never divide by zero, never guess)
    z = optimize_portfolio([snap("x", edge=0.05, vol=0.0)], [])
    check("zero vol -> zero", z["x"] == 0.0)


def test_huber_in_optimizer():
    # Extreme outlier edge with tight Huber band -> capped, not explosive
    wild = optimize_portfolio(
        [snap("w", edge=100.0, vol=0.1)], [],
        kalman_P0=100.0, kalman_c0=0.0, kalman_Q=0.0, kalman_R=0.01,
        huber_delta_vols=2.0, l1_limit=100.0, max_position=100.0)
    # posterior ~100, Huber caps at 2*0.1=0.2, Kelly: 0.25*0.2/0.01 = 5.0
    check("outlier capped by Huber*Kelly", abs(wild["w"] - 5.0) < 1e-9,
          wild["w"])


def test_edge_cases():
    check("empty snapshots -> empty dict",
          optimize_portfolio([], []) == {})
    try:
        optimize_portfolio([snap("a")], [], l1_limit=-1.0)
        check("negative l1_limit raises", False)
    except ValueError:
        check("negative l1_limit raises", True)
    # Per-market cap binds before L1
    out = optimize_portfolio([snap("a", edge=10.0, vol=0.01)], [],
                             l1_limit=100.0, max_position=2.0)
    check("per-market cap binds", abs(out["a"]) <= 2.0 + 1e-9, out["a"])


def main():
    test_kalman_fuses_prior_and_observation()
    test_huber_caps_outliers()
    test_optimizer_deterministic_and_pure()
    test_l1_constraint()
    test_volatility_scaling()
    test_huber_in_optimizer()
    test_edge_cases()
    print(f"--- {len(failures)} failure(s) ---")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
