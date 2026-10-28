# Nightwatch — an agentic framework for building calibrated, falsifiable agent systems

Nightwatch is a design pattern for multi-agent systems that treats every agent
output as a falsifiable claim. A coordinator dispatches bounded work quanta to
specialist agents and synthesizes fixed-size outputs; judgment is pre-registered
as executable gates rather than exercised as discretion at runtime; and every
probabilistic claim is scored against outcomes so miscalibrated components are
flagged by rule, not by intuition.

## The framework patterns

- **Coordinator fan-out.** Fetch → dispatch one bounded quantum per
  specialist → barrier → synthesize fixed-size outputs. No sequential chains.
- **Compiled mechanical gates.** Judgment is pre-registered as code and
  executed as math. The machine argues through falsification, not discretion.
- **Calibration loop.** Every probabilistic claim is Brier-scored at
  resolution against decay-weighted history; drift is flagged by rule.
- **Doctrine trip breakers.** The system's own rules carry kill conditions
  and trip automatically.
- **Agent foundry.** New specialists are bred from a charter template, each
  owning one differentiation axis, quarantined until scored output earns trust.
- **Shared data plane.** Fetch once per cycle into shared caches; per-agent
  re-fetching is a spec violation.
- **Two-tier execution.** A cloud agent head holds all judgment; a local
  execution tier on a consumer workstation does the bounded, verifiable
  work — wake-on-demand under reference-counted leases, an activity-aware
  sleep decider, and a hash-pinned clone swarm for parallel collection.
  The local tier holds no credentials and no commit path: if it goes dark,
  cycles get slower, never wronger. See
  [docs/execution-tier.md](docs/execution-tier.md).

## Reference implementation: prediction-market research engine

The framework's reference instantiation is a prediction-market research engine:
a coordinator dispatches bounded candidate evaluations to desk agents
(model-driven, sentiment-fade, contrarian, meta red-team), each returning a
fixed decision block. Every candidate must clear a compiled gate stack before
booking: quarter-Kelly position sizing with a 5-point expected-value band,
confidence-bounded entry gates (win probability minus uncertainty penalty
minus price must exceed the margin), pre-registered one-shot traps,
driver-concentration caps, and price-unit safety. Fills are depth-capped and
breadth-first; entries fail closed without a live depth snapshot.

## Repo layout

```
bin/            compiled gates: EV gate, traps, trip breakers, circuit breaker,
                Brier scoring, calibration, fill engine, bar registry
fixtures/       test fixtures: sample market metadata, driver taxonomy
docs/           architecture documentation, incl. the execution tier:
                wake leases, the sleep decider, and the clone swarm
harness/        workstation harness reference code (lease manager with the
                wake-need bridge; site configuration by environment)
kelly.py        quarter-Kelly sizing
optimizer.py    candidate optimizer
book_trade.py   the single booking path — all gates enforced here
test_*.py       executable specifications for the gates
run_tests.sh    one-command runner: every suite against sandboxed state
```

## Quick-start

```bash
./run_tests.sh                          # all suites, sandboxed state
python3 -m unittest test_book_trade     # gate stack: 48 tests, green
python3 test_traps.py                   # pre-registered trap semantics
python3 test_mikiri.py                  # confidence-bounded entry gate
python3 test_driver_gate.py             # driver-concentration caps
python3 test_optimizer.py               # candidate optimizer
```

Every suite stages its own fixtures through `testutil.py`: subprocesses
run with a sandboxed HOME, a sandboxed state dir (`NIGHTWATCH_STATE_DIR`),
planted poller quotes, and a stub order-book snapshot
(`NIGHTWATCH_BOOK_STUB`) — no suite touches live state or the network.
The stub book matters: entries walk a depth snapshot and fail closed
without one, so the harness plants a deep two-sided book at each test's
price instead of letting the fill path reach for a live venue. In
production the same code fetches the live book.

Requires Python 3.10+, standard library only.

## What's not here

This is a public edition excerpted from a larger private system. The
booking path, gates, calibration, fill engine, and lease harness in
this repo are complete and runnable; the surrounding operations are
not included: the hourly cycle worker and its audit steps, the
local-inference summarizer and its stream watchdog, the venue gateway
client, the doctrine and spec documents the code cites as policy, the
suites' companion proofs for a few `bin/` modules, and the swarm
launcher and merge tooling described in
[docs/execution-tier.md](docs/execution-tier.md) (§3 there is design
documentation; the lease manager in `harness/` is the shipped half of
that story). References in comments to those components describe the
private deployment, not files you failed to find.

## Honesty

This is paper-trading simulator infrastructure. There are no live positions,
no API keys, and no credentials anywhere in this repository. It is strategy
research code, not financial advice.

This repo is a public mirror of the private working system; its history
is squashed to a single commit at publish.
