#!/usr/bin/env python3
"""optimizer.py — Phase 3.1 portfolio optimizer scaffold.

STRICTLY OFF-PATH: pure stateless function. No I/O, no global state, no
production/hook/auth/booking/shadow-soak wiring. This is a research scaffold
for synthetic testing only — it does not read the ledger, does not place
trades, and is not called by any worker.

Pipeline:
 1. Kalman update: each market's noisy edge observation is fused with the
 prior (P_0, c_hat_0) to produce a posterior edge estimate.
 2. Volatility-scaled Huber cap: the posterior is robustified — outliers
 beyond delta*volatility are capped, not discarded.
 3. Edge → position: Kelly-style sizing (edge / variance), capped per-market.
 4. L1 portfolio constraint: if gross exposure exceeds the limit, scale all
 positions down proportionally (sparsity-preserving: zeros stay zero).

All inputs explicit. Deterministic given inputs.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketSnapshot:
    market_id: str
    price: float        # current price in [0, 1]
    volatility: float   # price volatility (std dev, > 0)
    edge_obs: float     # noisy observed edge signal (can be any real)


@dataclass(frozen=True)
class PortfolioPosition:
    market_id: str
    size: float         # current signed position size


def kalman_update(prior_mean, prior_var, observation, obs_var, process_var):
    """One scalar Kalman update. Returns (posterior_mean, posterior_var)."""
    # Predict (random-walk state: mean persists, variance grows)
    pred_var = prior_var + process_var
    # Update
    denom = pred_var + obs_var
    if denom <= 0:
        return prior_mean, prior_var
    k = pred_var / denom
    post_mean = prior_mean + k * (observation - prior_mean)
    post_var = (1 - k) * pred_var
    return post_mean, post_var


def huber_cap(x, delta):
    """Huber robustification: linear beyond |delta|, quadratic within.

 Returns the capped value. Preserves sign. If delta <= 0, returns 0
 (no trust in the signal at all).
 """
    if delta <= 0:
        return 0.0
    if x > delta:
        return delta
    if x < -delta:
        return -delta
    return x


def optimize_portfolio(snapshots, portfolio,
                       kalman_P0=1.0, kalman_c0=0.0,
                       kalman_Q=0.01, kalman_R=0.25,
                       huber_delta_vols=2.0,
                       l1_limit=10.0,
                       max_position=3.0,
                       kelly_fraction=0.25):
    """Pure function: (snapshots, portfolio, params) -> {market_id: target_size}.

 Args:
 snapshots: list[MarketSnapshot] — one per candidate market.
 portfolio: list[PortfolioPosition] — current holdings (informational;
 the optimizer outputs TARGET sizes, not deltas).
 kalman_P0: initial error covariance (prior uncertainty).
 kalman_c0: initial state estimate (prior edge belief).
 kalman_Q: process noise variance (how fast the true edge drifts).
 kalman_R: observation noise variance (how noisy edge_obs is).
 huber_delta_vols: Huber threshold in units of market volatility.
 l1_limit: max sum of |target sizes| (gross exposure cap).
 max_position: max |target size| per market.
 kelly_fraction: fractional Kelly multiplier on edge/variance sizing.

 Returns:
 dict mapping market_id -> target position size (signed float).
 Empty dict if no snapshots. Never None.
 """
    if not snapshots:
        return {}
    if l1_limit < 0:
        raise ValueError("l1_limit must be >= 0")
    if max_position < 0:
        raise ValueError("max_position must be >= 0")

    targets = {}
    for s in snapshots:
        if s.volatility <= 0:
            # No volatility estimate = no trade. Skip, don't guess.
            targets[s.market_id] = 0.0
            continue
        # 1. Kalman: fuse noisy edge observation with prior
        post_mean, _ = kalman_update(
            kalman_c0, kalman_P0, s.edge_obs, kalman_R, kalman_Q)
        # 2. Volatility-scaled Huber: cap outliers at delta vols
        capped = huber_cap(post_mean, huber_delta_vols * s.volatility)
        # 3. Edge -> position: fractional Kelly on estimated edge
        # size ~ edge / variance, scaled by kelly_fraction
        raw = kelly_fraction * capped / (s.volatility ** 2)
        # Per-market cap
        if raw > max_position:
            raw = max_position
        elif raw < -max_position:
            raw = -max_position
        targets[s.market_id] = raw

    # 4. L1 constraint: scale down proportionally if over the limit
    gross = sum(abs(v) for v in targets.values())
    if gross > l1_limit and gross > 0:
        scale = l1_limit / gross
        for k in targets:
            targets[k] *= scale

    return targets
