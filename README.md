# Nightwatch trading engine

Core gates and sizing machinery of Nightwatch, a prediction-market
research firm: quarter-Kelly sizing, mechanical EV gates, Brier-score
calibration, doctrine trip breakers that falsify the machine's own rules.

Paper-trading simulator infrastructure. No live positions, no API keys,
no credentials — nothing here can touch money.

## What's here

- `kelly.py` — quarter-Kelly sizing with the 5pt EV band gate
- `book_trade.py` — the only booking path; gates execute math, exit 3/4 on refusal
- `optimizer.py` — Kalman/huber-capped portfolio optimizer
- `bin/` — mechanical_gate, cycle_gate, brier, calibrate, trip_doctrines,
  traps, circuit_breaker, fill_engine, register_bar, recompute_scoreboard,
  epistemic, build_deltas, provenance, verify_spans
- `test_*.py` + `testutil.py` — tests (sandboxed HOME, write to temp dirs)
- `SPEC.md`, `DOCTRINES.md`, `PAPER.md` — spec, doctrine schema, paper ledger
- `desks/FOUNDRY.md`, `desks/TEMPLATE.md` — runner breeding procedure + charter
- `desks/WATCHLIST.json` (positions stripped), `hidden_files/driver_taxonomy.json`
  — static fixtures the gate tests need

## Quick-start

```bash
python3 -m unittest test_book_trade   # 48 booking-path + gate tests
python3 test_traps.py                 # D-004 pre-registered trap tests
python3 test_mikiri.py                # D-003 confidence-bounded EV gate tests
```

Requirements: Python 3.11+, standard library only.

## What's not here

No credentials, keys, live ledger, hook state, cron files, news caches,
or strategy secrets. `hidden_files/` and `hooks/` were deliberately
excluded except the two static fixtures above.
