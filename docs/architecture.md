# Nightwatch architecture

## Overview

Nightwatch is a framework for building agent systems whose outputs are
falsifiable claims rather than untestable prose. The core conviction: judgment
should be pre-registered as executable code and argued through falsification,
never exercised as discretion at runtime. The reference implementation — a
prediction-market research engine — is one instantiation; the patterns below
are the framework itself.

## 1. Coordinator fan-out

Each cycle runs a single coordinator with a fixed quantum:

```
fetch → dispatch one bounded work unit per specialist → barrier → synthesize
```

Every specialist receives at most a fixed input size and returns a fixed-size
decision block (for the reference implementation: ≤5 candidates in, ≤10-line
decision out). Sequential agent chains are banned: a chain of agents is a chain
of unexamined assumptions, and a growing mischief compounds quietly. A red-team
agent may run on a one-cycle lag for advisory kills, but never on the decision
path.

## 2. Compiled mechanical gates

Nothing discretionary executes. Every policy that can block or permit an action
is compiled into a gate module with a deterministic verdict. Gates are
registered through a single enforced path: a new gate or kill condition must
prove it can both trip and clear on synthetic data before it is admitted, and
every admission is appended to an append-only judgment log with a stated
`wrong_if` condition. A gate never seen to refuse something is unverified.

Kill-switch semantics: a trip file halts all new risk; exits stay live
("flatten, don't freeze"). Only an architect-level authority clears a trip.

## 3. Calibration loop

Every probabilistic claim the system emits is Brier-scored at resolution:

- Lifetime unweighted score plus a decay-weighted score (21-day half-life)
  with an effective sample size.
- Calibration is tracked per agent and signal family; tiers escalate by rule
  (watch, propose-recalibrate, escalate) as effective-n crosses thresholds.
- Mechanical exits feed a shadow tracker so stopped-out claims are still
  scored honestly.

Unscored agents exist (exploration, sandboxed) but are quarantined: they never
vote on the math and never dilute the calibration log.

## 4. Doctrine trip breakers

The system's own operating rules are registered as doctrines, each carrying a
kill condition and a revisit date. When a proposed change matches a kill-class
doctrine, the trip breaker fires automatically: a trip file is dropped and the
same halt path as the kill switch engages. The doctrines themselves are
hunted by the red-team agent, which attacks the rules at the code layer —
the framework expects its rules to survive adversarial review, not reverence.

## 5. Agent foundry

New specialist agents are bred from a charter template, not hand-assembled.
Each agent owns exactly one differentiation axis (data source, domain, thesis
family, horizon). Correlated agents are cost without information and are
culled. Every agent is quarantined in the foundry until it has produced scored
output; promotion runs through the same fixed gates as everything else.

## 6. Shared data plane

One fetch per cycle into shared caches; every agent reads the same caches.
Per-agent re-fetching is a spec violation. Caches carry TTLs and explicit
invalidation rules: prices (90s), metadata (on source change), settled
outcomes (immutable, never re-queried), candidate funnels (6h).

## 7. Reference implementation: the prediction-market engine

The reference instantiation applies the framework to prediction-market
research. Desk agents (model-driven, sentiment-fade, contrarian, meta
red-team) receive market candidates and return decision blocks; the
coordinator synthesizes them into bookings through `book_trade.py`, the
single booking path.

### Gate stack (all compiled, all deterministic)

- **Position sizing:** quarter-Kelly by construction, with a 5-point
  expected-value band below which no size is emitted. Per-trade caps, a daily
  loss cap, and drawdown limits bound the book.
- **Mechanical entry gate:** confidence-bounded — `win_p − k·σ − price` must
  exceed the margin, where σ comes from the agent's decay-weighted Brier
  history. Cold-start agents are exempt but labeled, so the exemption is
  visible in the log.
- **Pre-registered traps:** bounded one-shot decisions armed ahead of an
  event — at most five armed, one per market, fuse-limited, crash-safe.
  A trap authorizes the attempt, never the outcome; execution still passes
  the full gate stack.
- **Driver-concentration cap:** no more than two open positions on the same
  macro driver; a third is rejected.
- **Price-unit safety:** cents/dollars confusion is a reject, not a retry.
  Units must be verifiable against a live quote or the entry fails closed.

### Fill model

Fills are depth-capped and breadth-first: the worker's price is a limit, and
an entry-side walk filters asks above it so VWAP stays under the limit.
Entries fail closed without a live depth snapshot; exits fail open. Fees are
recorded per leg.

### Falsification

The replay simulator used for backtesting is frozen by design: falsification
and calibration only — it never trains on history. Backtest rows are tagged
and quarantined; live ledgers are untouched. Every pre-registration carries a
kill condition, and hand-computed unit tests precede the first run cycle.

## Design principles

- Discipline at runtime, judgment at registration.
- A threshold is not real until it is written with its trigger numbers.
- Context is the budget: bounded reads, cached repeats, capped outputs.
- Every failure becomes a spec update the same session — never a silent patch.
