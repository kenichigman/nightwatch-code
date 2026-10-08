<!-- BLOCK: FOUNDRY-identity -->
# FOUNDRY.md — the desk foundry (how rats are bred)

Gabe's directive 2026-09-24 ~08:12 CDT: "as many desks as possible... lots of
iterative rats running out testing any # of paths." K3N1, the architect-rat at
the center of the maze, breeds the runners. This file is the breeding procedure.
<!-- /BLOCK: FOUNDRY-identity -->

<!-- BLOCK: FOUNDRY-wheel -->
## The wheel (why the foundry exists)

Nightwatch is an information company. The product is priced beliefs, scored in
public; trades are one consumer. The wheel: **simulate → resolve → score →
recalibrate → sharper simulations.** The foundry feeds the wheel with runners;
the log sharpens them. The wheel moves itself as long as scoring stays honest.
<!-- /BLOCK: FOUNDRY-wheel -->

<!-- BLOCK: FOUNDRY-governors -->
## The governors (why not infinite rats)

Gabe's own law — context is the budget. Two governors cap the swarm:
1. **Context:** every desk's output must be read and synthesized by the hourly
   brain. N desks × handoff tokens = linear cost. Handoffs stay ≤15 lines;
   ledgers stay append-only; the brain reads ledgers, not charters, per run.
2. **Scoring bandwidth:** a desk without a ledger is noise. No charter without
   a book (or a stated meta-metric), no book without calibration scoring.
   The foundry breeds runners; the log decides which ones live.

Correlated rats add cost without information. Every new rat must own at least
one **differentiation axis**: source (RSS / social / deep-read / data),
domain (sports / politics / crypto / culture), thesis type (fades / quant /
unlock-events / experiments), or horizon (days / weeks / months).
<!-- /BLOCK: FOUNDRY-governors -->

<!-- BLOCK: FOUNDRY-pipeline -->
## The pipeline (where theses flow)

```
Q/C/F originate → theses scored in the log
    → gated winners graduate to M (mirror) → S (scale, 2%) → X (dream scale)
    → R red-teams on a one-cycle lag (kill-notes into the logs; paper books
      without waiting — a kill note flips its thesis R_REVIEW_PENDING →
      R_REVIEW_COMPLETE, which is what unblocks real-money nomination)
```

Graduation is upward only. A thesis that can't survive R's kill-note had better
have an answer for it in the decision log.
<!-- /BLOCK: FOUNDRY-pipeline -->

<!-- BLOCK: FOUNDRY-spawn-checklist -->
## Spawn checklist (breeding a rat)

1. Copy `desks/TEMPLATE.md` → `desks/<LETTER>.md`; fill every section.
2. Register the book in PAPER.md (bankroll, size, mandate, caps) — or state
   the meta-metric if the rat carries no book.
3. Give it a decision log (append-only, CDT) from birth.
4. Plug it into the hourly loop: append its mandate to the skill's
   PROCEDURE_NOTES.md so the brain runs it.
5. First run is a shakedown: the rat must produce one scored decision or one
   honest no-trade before it's a real runner.
6. Log the birth in the daily log.
7. Data-plane inheritance: the rat reads the shared caches + RAG — it never
   fetches prices/news/funnel data directly. New charters auto-index via the
   `desks/*.md` glob; no registration step.
<!-- /BLOCK: FOUNDRY-spawn-checklist -->

<!-- BLOCK: FOUNDRY-living-maze -->
## The living maze (2026-09-24)

Terminology (Gabe 2026-09-24 ~08:20 CDT): a **litter** = rats bred together;
a **mischief** = a group of litters. The swarm is the mischief.

A litter is also the unit of parallelism: the hourly brain dispatches one
runner subagent per litter per cycle (synchronous fan-out — see the skill's
execution model). Fixed quantum per desk: ≤5 candidates in, ≤10-line decision
block out. Breed litters the brain can run side by side.
<!-- /BLOCK: FOUNDRY-living-maze -->

<!-- BLOCK: FOUNDRY-litter-mischief -->
## Litter vs mischief (audit resolution 2026-09-24 ~08:50 CDT — both terms kept)

- **Litter** = one parallel batch dispatched per cycle. The unit of dispatch:
  one runner subagent per litter, fixed quantum per desk (≤5 candidates in,
  ≤10-line decision block out).
- **Mischief** = the managed set of live litters. Today: 1 (Litter 1:
  M/S/F/Q/C, hourly cadence). Future: e.g. a W/E/D litter on the same
  heartbeat or a different cadence — registered in
  `hidden_files/worker_state.json → mischief`.
- R and X are NOT dispatched in a litter: R red-teams on a one-cycle lag, X
  books after the barrier. They belong to the mischief, not to any litter.

| Rat | Axis owned | Book | Status |
|---|---|---|---|
| M | mirror (real-gate fidelity) | $10 / $1 | running |
| S | scale (2% sizing) | $500 / $10 | running |
| F | origination (experiments) | $10 / $1, 5/day | running |
| X | dream scale (sandbox) | $1M / $20k, unscored | running |
| Q | domain: sports-quant (.us) | $10 / $1 | newborn |
| C | thesis: sentiment fades | $10 / $1 | newborn |
| R | meta: red-team (kills theses) | none — kill ledger | newborn |
<!-- /BLOCK: FOUNDRY-litter-mischief -->
