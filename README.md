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
docs/           architecture documentation
kelly.py        quarter-Kelly sizing
optimizer.py    candidate optimizer
book_trade.py   the single booking path — all gates enforced here
test_*.py       executable specifications for the gates
```

## Quick-start

```bash
python3 -m unittest test_book_trade     # gate stack: 48 tests, green
python3 test_traps.py                   # pre-registered trap semantics
python3 test_mikiri.py                  # confidence-bounded entry gate
python3 test_driver_gate.py             # driver-concentration caps
python3 test_optimizer.py               # candidate optimizer
```

Two trap tests (`t6`) fail without a live order-book snapshot — the honest-fill
gate refuses to assume fills it can't verify. That's the gate working as
designed, not a bug; with a book snapshot present they pass.

Requires Python 3.10+, standard library only.

## Honesty

This is paper-trading simulator infrastructure. There are no live positions,
no API keys, and no credentials anywhere in this repository. It is strategy
research code, not financial advice.
