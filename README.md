# Nightwatch trading engine

Core gates and sizing machinery of Nightwatch, a prediction-market
research firm. This is the decision engine: quarter-Kelly sizing,
mechanical EV gates, Brier-score calibration, and doctrine trip breakers
that falsify the machine's own rules.

Paper-trading simulator infrastructure. No live positions, no API keys,
no credentials — nothing here can touch money.

## What's here

| File | What it does |
|---|---|
| `kelly.py` | Quarter-Kelly sizing with the 5pt EV band gate |
| `book_trade.py` | The only booking path; gates execute math, exits 3/4 on refusal |
| `optimizer.py` | Kalman/huber-capped portfolio optimizer |
| `bin/mechanical_gate.py` | Pre-booking gate chain (provenance + span checks) |
| `bin/cycle_gate.py` | Deterministic LIGHT/FULL/KILL cycle routing |
| `bin/brier.py` | Brier-score calibration with 21-day half-life decay |
| `bin/calibrate.py`, `bin/local_calibrate.py` | Calibration tiers (ok/watch/reinforce/recalibrate/escalate) |
| `bin/trip_doctrines.py` | Doctrine kill-breaker (D-001/D-003/D-004) |
| `bin/traps.py` | Pre-registered bounded traps (≤5 armed, 59-min fuse) |
| `bin/circuit_breaker.py` | Consecutive-fault circuit breaker for LLM components |
| `bin/fill_engine.py` | Depth-capped fill model (breadth-first, $2,000 clips) |
| `bin/register_bar.py` | The only registration path for new kill conditions/metric bars |
| `bin/recompute_scoreboard.py` | Ledger-derived scoreboard (X desk unscored) |
| `bin/epistemic.py`, `bin/build_deltas.py` | Epistemic gates + review-delta builder |
| `bin/provenance.py`, `bin/verify_spans.py` | Mechanical-gate dependencies |
| `test_*.py`, `testutil.py` | Unit/integration tests (all pass, see below) |
| `SPEC.md`, `DOCTRINES.md`, `PAPER.md` | Spec, anti-orthodoxy doctrine schema, paper ledger |
| `desks/FOUNDRY.md`, `desks/TEMPLATE.md` | Runner breeding procedure + charter template |

## Quick-start

```bash
python3 -m unittest test_book_trade   # booking path + gate tests
python3 -m unittest test_traps        # D-004 pre-registered trap tests
python3 -m unittest test_mikiri       # D-003 confidence-bounded EV gate tests
python3 kelly.py                      # quarter-Kelly sizing demo
```

All tests sandbox `HOME` — they write to temp dirs, never touch a real ledger.

## Requirements

Python 3.11+, standard library only. No third-party dependencies.

## What's not here

No credentials, no API keys, no live ledger, no hook state, no cron
files, no news caches, no strategy secrets. `hidden_files/` runtime state
and `hooks/` were deliberately excluded; the two exceptions are static
fixtures the gate tests need: `hidden_files/driver_taxonomy.json`
(driver vocabulary) and `desks/WATCHLIST.json` (paper-position fields
stripped for publication).
