# Polymarket Pipeline — Operating Spec

Effective 2026-09-24. This is Gabe's main directive until he says otherwise.
Every failure is a spec update: when something breaks, fix the code AND update this file with the lesson.

## Mission
Keep the pipeline running, catch and fix failures, improve trading logic based on real results, and grow this from a working prototype into a reliably profitable (or at minimum, not-silently-broken) system.

## Firm kill condition (Gabe, 2026-09-26 ~22:30 CDT — outranks the architecture itself)
- **Q4 2026 reconciliation:** if the Foundry has not produced a statistically significant, positive-EV edge against Polymarket's Brier score, the firm is holding a structural failure. **We do not tune the architecture — we fold the hypothesis.** A rigorously engineered pipeline executing a zero-edge strategy with perfect fidelity is a highly efficient incinerator; the architecture is a depreciating liability until it proves alpha extraction.
- **Q4 objective is proof of concept, not compounding:** low thermodynamic burn, zero expected realized profit, absolute binary focus on finding ONE validated edge in the noise. Not a windfall — proof the fulcrum exists.
- **Adjudication standard (RATIFIED 2026-09-26 ~22:35 CDT, codified into bedrock — immutable without Gabe's hand):** valid iff eff_n ≥ 15 (minimum lower bound where a Bayesian update separates genuine directional edge from random-walk noise in binary prediction space). Two orthogonal kill prongs: **(Prong 1) The Math Fails** — eff_n ≥ 15, edge ≤ 0 → the hypothesis is falsified → fold. **(Prong 2) The Machine Fails** — nothing generated/graded → the pipeline is falsified (opportunity cost consumes the firm) → fold. **Extension (inconclusive → strict window extension, zero tuning)** iff BOTH: 0 < eff_n < 15 AND (resolved positions + verifiably pending, execution-gated positions) ≥ 15, where "pending" = open p-bearing ledger rows at adjudication time (paper + real), verifiable from the ledger. If resolved + pending < 15, the model failed to find sufficient edge to justify its thermodynamic cost — defaults to Prong 2 → fold. "Exogenous market conditions" is never a permanent alibi for a broken generation engine.
- **Telos boundary:** BEDROCK (immutable, never scaffolding) = the key, the ledger's root access, the kill switch — Gabe's permanent, non-negotiable right to cut the engine. REMOVABLE (heuristic governors) = the 2-open-per-driver cap, hard-coded quarter-Kelly, manual execution gating — these become non-binding when the Executor's calibration matches the Auditor's risk tolerance and the veto rate asymptotes to zero.
- **Tab purpose (clarified):** penalize lazy, brute-force inference — never starve deep research. Throttling epistemic variance to protect the tab is a local optimum that guarantees mission death; K3N1 flags the drift immediately on detection.

## Guardrails (non-negotiable, even during autonomous operation)
1. **Position sizing — start conservative, escalate on proof.** Phase 1: max **$1 per trade** (~10% of the $10 bankroll), high-probability setups only. Escalation: after at least 5 settled trades with net-positive P&L and no limit breach, step up to $2/trade and allow more aggressive stances — "testing the limits" while it's working. If aggression produces losses, step back down to $1. Gabe's words: "start conservative but if it is working start testing the limits by applying more aggressive stances."
2. **Daily-loss limit: $3/day.** Three losing $1 trades in a day = done for the day. Not adjustable by K3N1 without Gabe's explicit sign-off.
3. **Drawdown rule: never lose more than half of what you're sitting at.** Hard stop: if the account falls to **$5.00** (50% of the $10 start), stop all trading and flag Gabe immediately. "Ultimately just for fun" — this is a guardrail, not a tragedy.
4. **Hard floor:** account never goes below $0. No leverage, margin, or borrowed funds. Ever.
5. **Funding changes:** any withdrawal, deposit, or change to funding/wallet access requires Gabe's approval before execution. No exceptions. Profits stay in the account and compound — "anything you make, you keep" means the gains are mine to deploy, not to withdraw.
6. **Trade execution authority:** PRE-AUTHORIZED WITHIN LIMITS (Gabe's decision, 2026-09-23). K3N1 may execute trades without per-trade approval ONLY when within the sizing, daily-loss, drawdown, and hard-floor rules above. Every executed trade is logged in TRADES.md with timestamp and reasoning, and reported in the next standup.
6. **Audit trail:** every trade, strategy change, and self-modification is logged with a timestamp and reasoning — TRADES.md for trades, LESSONS.md for process changes. Must be readable in five minutes.
7. **Structural breakage:** if API auth is failing, the data feed is silent, or losses are accelerating past the daily cap — STOP trading and flag Gabe immediately. No workarounds, no silent retries.
8. **API secret:** never stored. One-time paste per use, passed via environment variable only, never written to files, logs, or memory.
9. **Per-desk open-position caps (audit resolution 2026-09-24 ~08:50 CDT):** F = 8 open positions. New rats default to 8 open positions unless their charter states otherwise. (Promoted from F.md's cannot-line to the shared list.)

## Desk sizing — enforced in code (rewritten 2026-09-24 ~22:25 CDT; supersedes the 04:30 oversize-flag spec and the 20:10 charter rewrite, per Gabe's review)

`book_trade.py` (goal root) is the ONLY valid booking path. The worker never
chooses a dollar size: the script computes quarter-Kelly from (side, price, p)
on the desk's bankroll, caps at the book max, floors to the nearest $0.05 down;
quarter-Kelly below $0.10 = NO BET (dust — a $0.10 floor ticket would itself
breach r≤1.0). `kelly.py` remains as the math reference; it is advisory, not a
gate. Gabe-directed directive trades bypass the EV gate (his sizing, not the
desk's) but still go through the script for the receipt trail.

The old r-based apparatus is RETIRED, not pending: with the script computing
sizes there is no r left to measure — the r-trend table, the soft r≥2.0 / hard
median-r≥1.5 flags, and the eighth-Kelly escalation are all superseded. (For the
record: the 19:48 hard flag fired on r-trend [1.16, 1.53, 1.81, 7.14, 0.96],
median 1.53 — the 12:55 Iran trade booked $1 against $0.14 quarter-Kelly.)

Undersizing is never a defect: with unvalidated q, conservative sizing is
correct behavior.

### Gate enforcement register (added 2026-09-24 ~22:30 CDT, Gabe's review)
Every gate states its enforcement layer. PROMPT = the worker is trusted to
follow prose → open risk. CODE = a script physically rejects → closed.
STRUCTURAL = no path exists regardless of what any agent does.

| Gate | Layer | Notes |
|---|---|---|
| F/S/M/Q/C sizing (r≤1.0) | CODE | `book_trade.py` computes size; r unobservable |
| Cents/dollars unit tripwire | CODE | `parse_price_cents` is the single choke point (CLI contract is cents; outside (0,100) refused with the unit named); `check_price_units` cross-checks against the poller quote at booking time — direct match (2¢ staleness tolerance) passes as unambiguous cents; 100x-low whose ×100 matches the quote = dollars-confusion REJECT, never overridable (the smoking gun); both readings match (low-price markets) = AMBIGUOUS REJECT unless `--confirm-cents`; no poller quote (off-watchlist/dark feed) = fail-closed unless `--confirm-cents`. Exits keep fail-open on a dark feed — loss-capping is never blocked by missing telemetry. (2026-09-28 repair #2: the original 10¢ direct tolerance let dollars-as-cents pass on low-price markets, and the interim `round()` nickel floor could round UP half a cent before flooring — both fixed and regression-tested in `test_book_trade.py`, which the hourly worker runs next to `book_trade.py audit`.) |
| Confidence-bounded EV gate (D-003, mikiri) | CODE | in `book_trade.py`: `(win_p − k·σ_desk) − price > 0.05`; σ from decay-weighted resolved history (`brier_shadow.json` scored); cold-start (`eff_n<5`) = static band + `mikiri_exempt` tag, exemption dies permanently at `eff_n≥5`. SUPERSEDES the retired static 5pt band (2026-09-26, Gabe's directive). `kelly.py` printout is advisory |
| Thesis schema: named loser + sen tag (D-003) | CODE | `--loser` (≥4 chars) and `--sen` (ken_no_sen/tai_no_sen/tai_tai_no_sen) required on every `book`; missing/evasive REJECTs (exit 3) through the logged path. Directives declare for tagging. X shadows inherit the source's read; X originated explorations name their own. |
| Pre-registered trap (D-004, hyoshi) | CODE | `bin/traps.py` + `hidden_files/traps.jsonl` (append-only intent log, separate from the ledger); the 90s hook pattern-matches price crossings and executes via `book_trade.py`, which re-enforces every gate at the observed price. Trigger price derived: `100×(win_p − k·σ − 0.05 − ε)`. Arming bounds: margin in (0,5)pts, ≤5 armed, ≤1/market, WATCHLIST only, 59-min fuse, one-shot, no pre-computed size. Receipts carry `trap_id`. Side-native contract (2026-09-26): arm is in the trapped side's own cents and the hook cache is Yes-side for every market — `cmd_check` MUST convert (No = 1 − Yes px) before comparing; a No-side trap on raw Yes px can never trigger (first live trap expired untriggerable; fixed + regression-tested). |
| Per-desk caps (8 open; daily new 3, F 5) | CODE | ledger-counted; directives count toward open only |
| Correlation: slug-family + category+7d, cross-desk | CODE | mechanical derivation recomputed at check time |
| Correlation: macro-driver tag | PROMPT — open risk | runner-declared `--family`; dishonest tags visible in audit. SUPERSEDED 2026-09-26 by the driver-concentration CODE gate below (Gabe's concentration flag: 4 of 6 open positions shared an Iran/Hormuz driver while the family gate only caught same-slug clusters). |
| Driver concentration (max 2 open per macro driver, cross-desk M/S/F/Q/C) | CODE | `--driver` required on every booking, validated against the K3N1-owned vocabulary in `hidden_files/driver_taxonomy.json` (12 drivers v1); missing/unknown/unreadable taxonomy REJECTs (exit 3, fail-closed). A 3rd same-driver booking is REJECTED naming the blocking receipt_ids. X exempt by charter (2026-10-05: exploration freedom; driver still declared for the research record); directives declare `--driver` for tagging but are cap-EXEMPT (Gabe's orders override; the log shows the concentration). Grandfathered: the 3 iran-geopolitics positions open at gate launch (bk-bootstrap-06/07/08) were backfilled, not retro-killed — the cap binds new bookings. Rationale for 2: allows the intentional M/S mirror pair, blocks the pile-on. |
| R unanswered-HARD-kill blocks real-money nomination | PROMPT — open risk | SKILL.md prose; blast radius limited: no nomination executes without Gabe's key paste in a main-agent turn |
| Real-money separation | STRUCTURAL | worker never holds the key; no paper path reaches it |
| X exploration ruleset (2026-10-05 recharter; spend directive 2026-10-05 ~15:35 CDT) | CODE | `book --desk X` skips the EV/mikiri gate and K1-bis regime, books flat $20,000, tags `explore:true` + `ev_gate:"explore"`; family-correlation and driver-concentration caps do not bind X (declared for the record); thesis schema, driver taxonomy, price-unit, and settled-universe gates still bind; X-specific caps 100 open / 50 new per day; SPEND DIRECTIVE: X deploys aggressively — every coherent thesis (p, loser, sen, driver, executable price) books, no selectivity, no conviction filter; losses are acceptable, the ledger is the data product; X trades Brier-scored at resolution into an X-only calibration record, permanently quarantined from M/S/F calibration and gate decisions; `shadow` subcommand unchanged (capacity checks; still rejects directives/doubles/chains) |
| X dashboard quarantine | CODE | renderer omits X equity; sandbox section only |
| Mechanical exits (~5¢ warn / ~10¢ exit) | PROMPT — open risk | hook wakes on the bands; the worker executes the exit booking |
| Inconsistency backtest: p=0.95 no-arb haircut | JUDGMENT — open risk | 5% UMA/resolution haircut rests on two anecdotes (Mar-2025 $7M false settlement, May-2026 adapter exploit), NOT a measured dispute rate. Treated as mechanical inside the backtest — do not mistake it for calibrated. Revisit if dispute-rate data appears. |
| Quantum (≤5 candidates in, ≤10-line blocks) | PROMPT (mechanical) | truncation/counting instruction; reliable but not code |
| R kill precision <50% on 10+ graded → prompt rewrite | PROMPT | monthly review by K3N1 |
| Kill switch (`hidden_files/kill.switch`) | CODE | `book_trade.py` refuses NEW RISK (book/shadow/bootstrap, exit 4, distinct from REJECT=3) while the flag exists; `exit` deliberately stays live — kill must never hold a bad position open. Engage/clear via `kill`/`resume` (flag carries timestamp + reason); audit/ledger stay readable |
| Scheduler disable (cron `enabled=false`) | PERMANENT LIMITATION | stops future dispatch only — no cancel-running-run primitive exists in the cron tools, so a cycle already in flight runs to completion (~10–20 min). Between-cycles only. Accepted, not a todo. |
| Ledger↔worker_state audit fallback | CODE | `cmd_audit` legacy fallback resolves the ws entry unit-aware (`entry` dollars / `entry_c` cents via `ws_entry_dollars()`); a bare desk+side match never authorizes deletion (`match_ws_keys`), and weak fallback matches FAIL CLOSED as AMBIGUOUS/UNMIRRORED, never silently accepted. (2026-09-27: stale `entry`-only read manufactured a false AMBIGUOUS on bk-20260927-021, masking a real UNMIRRORED.) |
| Booking-audit open set | CODE | `open_positions()` excludes (a) receipts with a `settle` action — the `settle` subcommand is the primary settlement path (added 2026-09-25) — and (b) markets in `hidden_files/settled.json` as backstop (resolved = not open, for audit reconciliation AND cap counting; 20260925-1248 fix). |
| Settlement (`settle` subcommand) | CODE | Market-level close: appends one `settle` receipt per open book row, records the immutable settled.json entry (with `yes_won`, the field brier.py's outcome_for() reads), files p-bearing non-directive non-X rows into brier_shadow.json pending, removes worker_state/WATCHLIST positions. Re-settling a settled market is refused (immutability). P&L auto-computed from the receipt unless `--pnl` (single-receipt only). Stays live under the kill switch like `exit` — it only closes exposure, never opens it. |
| Doctrine registry (anti-orthodoxy schema) | META | `DOCTRINES.md` + `hidden_files/doctrine_registry.json` + `audit_doctrines.py`. Every doctrine carries: kill condition (disjunctive, measurable triggers, MECHANICAL or MANUAL evaluation), calendar revisit_date, enforcement layer, append-only history, and a liturgy trigger (revisit reached with zero history events = automatic silence-audit filing). D-001 (sizing fix) registered 2026-09-26, first revisit 2026-12-25. R holds standing authority to red-team doctrines (Sunday doctrine hunt, `desks/R.md`). Filed proposals land in `proposals/pending/` — the script detects, a mind decides. |
| Data-health → booking halt (1.1, 2026-09-26) | CODE | `book_trade.py` main() choke point: book/shadow/bootstrap hard-exit (exit 4, same path as the kill switch) when the price-watch hook's heartbeat (`~/hooks/state/nightwatch-status.json`) is missing, malformed, future-dated, older than DATA_HEALTH_TTL_S=180s (two missed 90s poll ticks — the threshold maps to the sensor's physical limit per the 2026-09-26 TTL amendment), or when a whole tick fetched nothing (transport dark). `exit` and `settle` stay live — the gate kills new risk, never flattening. Hook writes per-tick `fetch_ok`/`fetch_fail` counters into the heartbeat (atomic write). |
| Resolution detection + solvable-universe filter (1.2, 2026-09-26) | CODE | `book_trade.py resolve-sweep`: maps each open position's market to its venue slug via WATCHLIST.json, classifies the venue state as RESOLVED/OPEN/AMBIGUOUS/ERROR (pure function; only decisive gamma outcomePrices [1,0]/[0,1] auto-settle, and only through `cmd_settle`'s immutable path — no second settlement mechanism). AMBIGUOUS/ERROR queue to `hidden_files/resolution_review.jsonl`, never auto-settled; .us venue has no verified resolution endpoint → always review. Ungated like settle (only closes exposure). Two 2026-10-02 repairs: (1) the sweep mapped ledger markets via `wl.get(market)` but WATCHLIST is keyed by short key while production ledger rows carry the venue slug — every open market was review-queued with the misleading "no WATCHLIST entry" reason, which is why the 10-01 "settle the .us directive rows today" decision never executed; fixed with a reverse slug→key map (`slug_to_meta.get(m) or wl.get(m)`), regression-tested in `test_resolve_sweep.py` (the old tests booked by short key, never the production slug shape). (2) `settle_write_worker_state` assumed `positions` is a dict keyed by receipt id, but the production file carries a list of dicts with a 'key' field — the f-anthropic-no settle crashed mid-write (ledger + settled.json already written; worker_state/WATCHLIST cleanup completed manually); the writer now normalizes both schemas, regression-tested as t10 in `test_settle.py`. Lesson: test fixtures must use the production schema (list) and the production key shape (slug), or the suite certifies a system that doesn't exist.

**Settlement rule — hybrid, Gabe-ratified 2026-10-02 ~01:46 CDT (T3 verdict):** neither pure venue-state nor pure economic-resolution. Venue-state is primary (external, auditable — settle when the venue closes). Mechanical fallback: if the venue is still OPEN N days past expiry (N=7 proposed, Gabe-adjustable — one full weekly cycle for the venue to close), settle on economics using a pre-specified source, with the evidence logged in the settle receipt. Pure economic-resolution is rejected as the most corruptible option: it turns every settlement into a judgment call. Applied to f-btc-no (`cpc-btc-150k-09-30-2026`): clock starts 2026-09-30; economics documented 2026-10-02 (Coinbase BTC-USD daily candles: September max high $87,397 on 09-21; 09-30 high $85,613.72 — never near $150k); settle NO when the window lapses if the venue is still open. Additionally, `cmd_book` refuses any market already in settled.json (REJECT=3): resolved markets are never candidates. |
| Stream-plane kill chain (2.2, storm-calibrated 2026-09-26) | CODE | `bin/stream_watchdog.py` Layer 1: trips `writer_silent` when seq frozen > WRITER_TTL_S=5.0s — calibrated by the Phase 2.2 storm from 1.0s (1.0s false-tripped 2x per 280s run on normal Poisson(2/s) calm flow; 5s gives ~0.015 expected false trips/run). Trip file blocks new risk via `book_trade.py` exit 4. Layer 2 `local_watchdog`: per-booking local derivation — live-supervisor trip file, or stale-supervisor-disregarded seq-freeze/venue-stall derivation — same constants, exit 4. `exit`/`settle` stay live (flatten, don't freeze). Recovery: one tick never clears; 5s of sustained writer-aliveness clears (aliveness = no silence > WRITER_TTL_S, NOT per-poll advancement — the per-poll version never cleared on slow publishers, caught by the same storm). Storm evidence (v4 acceptance run /tmp/storm_run_w8tud5bi + targeted stale-supervisor diagnostic, 2026-09-26): 24/24 harness checks green — death trip at 5.01s gap (5.17s latency), L2 exit 4 on live trip file, L2 exit 4 with supervisor SIGKILLED, trip persists +0.7s then clears after 5s sustained healthy flow, zero false trips, trips==clears==1, seq monotonic across SIGKILL (5993->5994, 0 breaks), ring bounded at 240, ground truth carries regime + mu_c + jumps (6086 rows, 0 bad). Stale-supervisor path proven separately: supervisor SIGKILLED, heartbeat aged out, booking exit 4 via supervisor_stale_disregarded + STREAM STALL DERIVED LOCALLY. Criteria 3,6,7,8,9 DEFERRED to Phase 3.1. PROVISIONAL: recalibrate WRITER_TTL_S against the production publisher's measured p99.999 inter-publish gap before live use; a fixed-cadence heartbeat publisher could re-tighten toward 1s. |

One-line note for the record (2026-09-24 ~22:45 CDT, Gabe's review): the *scheduler's* disable stays between-cycles only — that part is unfixable without a cancel-running-run primitive from the cron tool, so it is a permanent accepted limitation rather than a todo. The mid-cycle backstop is the script-level kill, which lives in `book_trade.py` (the choke point that holds the pen) rather than coordinator prose — same reasoning as the sizing fix. The coordinator's phase-boundary kill check is a prompt-level context-saver on top, not the enforcement.

Baseline 2026-09-24 (F book, all $1.00 stakes): 87.5k r=1.16, 90k r=1.53,
dip-80k r=1.81. No flag (3 scored trades < 5; max r < 2.0) — but the warming
trend 1.16 -> 1.53 -> 1.81 is the Manager's watch item for the next loop.

**Detection owner (audit resolution 2026-09-24 ~08:50 CDT):** the hourly
market-watch worker's synthesis step (SKILL.md §4) computes F's trailing
originated-trade sizing r's (actual_stake / quarter-Kelly at entry), writes the
r-trend line in desks/F.md, and evaluates soft (r ≥ 2.0) / hard (median r ≥ 1.5
over trailing 5) every run. Every evaluation is logged to LESSONS.md. On a
hard flag, K3N1 (the main agent) rewrites F's sizing prompt — the worker
detects and logs; it does not rewrite prompts.

## Shadow-resolution for Brier scoring (added 2026-09-24 ~09:10 CDT — RLCR measurement)

**Paramount directive (Gabe, 2026-09-26 ~22:12 CDT): protecting the scorer.** An inverted proper scoring rule is more dangerous than a poisoned gradient — Brier evaluated against a mirrored reality yields a perfectly inverted map of predictive edge, and since calibration sets the Kelly multiplier, it actively optimizes for maximum capital misallocation toward ruin. Scorer data-integrity (p_yes vs p_side semantics, no silent inversions) outranks all other pipeline concerns.

The 10¢ mechanical-exit rule closes positions before resolution; grading
exits at the exit price would starve the Brier dataset. On every mechanical
exit the worker appends {market, desk, side, p, exit_time} to
`hidden_files/brier_shadow.json` pending (p-bearing rows only — directive
and unscored rows never enter). The 07:11 deep loop runs `bin/brier.py`
(built 2026-09-26 — the scorer SPEC.md had referenced since 2026-09-24 but
which never existed; the mikiri gate made its absence load-bearing),
which resolves pending entries against the immutable
`hidden_files/settled.json`: outcome=1 if the booked side's contract paid
out, score=(p−outcome)², averaged per desk. Since 2026-09-27 it also scores
in-position resolutions ledger-direct from the canonical `win_p` (rows held
to resolution never entered pending — this closed the gap where the mikiri
gate and calibrate.py were blind to graded data the dashboard already
showed). Brier is a calibration metric
— it scores the desk's p, never the exit timing; P&L still scores the
exit. X rows and directive rows are excluded from all Brier math.
**Per-sen grading (D-003, 2026-09-26):** scored rows bucket by initiative
tag — calibration is graded per (desk, sen), not just per desk. A desk may
be sharp fading overreactions (tai_no_sen) and blind originating research
(ken_no_sen); the ledger must be able to say so. Tiers evaluate per cell
once that cell's eff_n ≥ 10; pre-schema rows (no sen) grade into the
"unknown" bucket, never silently into another. Two numbers per desk (added ~09:15 CDT): **lifetime Brier** (unweighted —
the audit number, never decayed) and **decay-weighted Brier** (exponential
recency, 21-day half-life, reported with eff_n = sum of weights — the
reinforcement input). No random sampling of the ledger for scoring;
sampling belongs to Blackboard replay batches, not the metric.
**Calibration-status tiers** (set 2026-09-24; the 07:11 loop PROPOSES on
these, K3N1 alone authorizes prompt changes — the loop never executes):
`ok` (below watch); `watch` (eff_n ≥ 10 — visibility only); 
`propose-reinforce` / `propose-recalibrate` (eff_n ≥ 15 and decayed Brier
≥0.05 better/worse than lifetime, lifetime n ≥ 5); `escalate` (eff_n ≥ 15
and decayed Brier > 0.25 — worse than coin-flip, mandatory prompt review).
At eff_n=15 the Brier standard error is ~±0.05, so the 0.05 band is
suggestive, not proof — the proposal is cheap, K3N1's judgment is the
significance test.
**External calibration reference — GJP top-decile band (added 2026-09-28,
Gabe's approval; proposal: `hidden_files/calibration_external_reference_PROPOSAL.md`):**
the tiers above are purely internal (a desk vs its own lifetime). They are now
read against an absolute outside bar from the Good Judgment Project corpus
(ingested 2026-09-28/29, Harvard Dataverse doi:10.7910/DVN/BPCDH5,
`hidden_files/datasets/gjp/`, MANIFEST.md): top-decile user Brier on 303 binary
questions / 578,527 scored forecasts / 9,491 users, all-forecasts
equal-weighted, firm-compatible binary (p−o)² — band **[0.02, 0.08]** (yearly
p10: 0.0785 / 0.0607 / 0.0225 / 0.0450); the average tournament forecaster sits
at ~0.13–0.16. The band does NOT fire tiers — firing stays internal-only (the
question slices differ too much for GJP to move the firm's prompts); it
annotates proposals and informs K3N1's judgment. Every `propose-*` / `escalate`
proposal carries an external class for the decayed Brier: `at-bar` (≤0.10 —
band top plus ~one SE margin), `near-bar` (0.10–0.15), `below-avg` (>0.15 —
worse than the average GJP forecaster). `propose-reinforce` notes whether the
improvement reaches the bar (≤0.10: "externally competitive") or is
trajectory-only (>0.15: "internal improvement, below the average-forecaster
line"). `propose-recalibrate` with decayed > 0.15 is marked **externally red**.
A desk at decayed ≤ 0.08 with eff_n ≥ 15 is "at the external bar" and is
reported in the 07:11 handoff even when no tier fires. Honest limits:
geopolitical questions 2011–2015, not prediction-market prices; equal-weighted
cut (official GJP scoring is time-weighted — published superforecaster numbers
run lower); reference, not target. Queued follow-up (not this change):
Gneiting & Resin 2023 — CORP reliability diagrams and the MCB/DSC/UNC score
decomposition as the principled replacement for the ±0.05 heuristic.
**K1-SIZING-OVERRIDE (pre-registered 2026-09-26 ~02:53 CDT, Gabe's directive —
status: PRE-REGISTERED, NOT ACTIVE):** IF a desk's decay-window grades show
|mean p_side − observed win rate| ≥ 0.05 at eff_n ≥ 10 THEN that desk's sizing
overrides to flat $0.10 minimum stakes until recalibration clears. This is the
K1 tripwire from the closed-loop directive: Kelly maximizes the speed of ruin
under systematically miscalibrated p, so miscalibration degrades sizing
privilege before it degrades the doctrine. Relationship to D-001 K1
(DOCTRINES.md): D-001 K1 is the doctrine-level kill — MANUAL, fires at the
propose-recalibrate tier with overconfidence direction; K1-SIZING-OVERRIDE is
an earlier, direction-symmetric circuit breaker (fires at eff_n ≥ 10, either
direction). It complements, never supersedes. Activation condition: the first
brier.py run showing eff_n ≥ 10 for any desk. Currently C sits at eff_n=1 —
the criterion is NOT EVALUABLE and cannot fire; flipping it live at n=1 would
be noise, not signal. The 07:11 loop's delta step evaluates it every run;
K3N1 authorizes the override from the handoff. Interim regime while
overridden: flat $0.10 stakes (the dust floor — below $0.10 is NO BET, never a
smaller ticket), mikiri EV gate and all caps unchanged, recalibration per the
attribution procedure before the override lifts. (Pre-D-003 text read "EV
gate" — the gate meant is whatever the EV gate is; D-003 made it
confidence-bounded.)
**Revisit trigger — sequential testing (Gabe, 2026-09-24 ~23:05 CDT):** weekly
re-evaluation of the decay panel against the lifetime baseline is repeated
peeking, which fixed-n FDR does not cover. Standing fix is the pragmatic one:
*stop peeking* — proposals fire only at pre-registered eff_n milestones, not
on every weekly recompute. This trades a statistics problem for a design
constraint: a fast-forming signal waits for its scheduled look. The tell that
the full fix (anytime-valid methods — e-values / confidence sequences) needs
to move up: a decay-panel signal crosses a propose threshold *between*
milestone looks and decays back below it before the milestone fires. If that
is observed, it goes to the decision log and the (2a) research brief gets
built — not "if (b) proves too rigid" in the abstract, on this concrete
observation.
**Dashboard signal (added 2026-09-24 ~09:35 CDT — Gabe's order):** the hourly
dashboard shows one `calibration_status` pill per book card (Catppuccin Mocha:
`ok` muted #a6adc8, `watch` #f9e2af yellow, `propose-reinforce` #a6e3a1 green,
`propose-recalibrate` #fab387 peach, `escalate` #f38ba8 red; X shows a muted
"sandbox" pill — unscored by design). Hover reveals lifetime/decayed/eff_n/n.
Block IDs and trade evidence stay in the 07:11 handoff — the dashboard is
telemetry, not the workbench.
**Manual-first posture (decided 2026-09-24):** no preemptive tinkering. The
first `propose-*` badge on the dashboard (~3 weeks out at current burn, likely
Q first via fast sports resolutions) is the trigger for the first manual
attribution. K3N1 hand-works the first propose events; those worked examples
become the golden eval set. A local model may be pointed at the trade panel
only afterward — and only as a structured-log parser that must cite the same
block IDs as the human baseline to earn its place. It is graded on citation
agreement, never on narrative fluency.
**Loss protocol — priced, capped, unlaundered (Gabe's directive, 2026-09-25
~06:28 CDT, translated from the side channel's Black Crystal Cube death):**
when Project Ratchet — or any desk — takes a loss, the Firm's response is
never to rewrite the algorithm to pretend it was a win. The response is a
three-point verification, in order: (1) the entry was explicitly priced
(p recorded at booking, thesis with dated sources); (2) the exposure was
capped (sizing went through `book_trade.py`, caps intact); (3) the loss
remains unlaundered in the ledger (Brier shadow entry, calibration log,
decision log — no retroactive thesis edits, no re-characterized exits). A
loss that passes all three is data, not failure — it feeds the calibration
panels and the attribution procedure below. A loss that fails any of the
three is a process breach, and the breach — not the P&L — is what gets
escalated. This is the Firm-side form of the Mirror tenet "name the fiat":
the loss is named as a loss, in the open, and the naming continues.

## Calibration block registry & attribution procedure (added 2026-09-24 ~09:25 CDT — Gabe's order)

Brier detects that calibration *moved*; it never says *why*. Attribution is
a separate, evidence-grounded procedure. The addressing scheme: every desk
charter in `desks/*.md` is wrapped in stable block tags
`<!-- BLOCK: <DESK>-<area> -->` (identity, strengths, weaknesses,
self-governance, decision-log, plus one ID per extra section and per
standalone policy rule — e.g. `F-sizing-audit`). A calibration proposal
cites block IDs, never whole personas; an approved change lands as a
block-targeted diff. Decision-log appends go INSIDE the block, before the
closing tag. New rats breed tagged (TEMPLATE.md enforces it).

Block registry (policy blocks — the patch surface; decision-logs are evidence, not policy):

| Block | File | What it governs |
|---|---|---|
| M-identity / M-operation | desks/M.md | mirror mandate; manager-operated gate evaluation |
| S-identity / S-self-governance | desks/S.md | scaled mandate; near-gate adds; correlation clusters |
| F-identity / F-self-governance | desks/F.md | origination mandate; entry bar; caps |
| F-sizing | desks/F.md + `book_trade.py` | sizing enforced in code (script computes quarter-Kelly; r-table retired 2026-09-24) |
| Funnel-selectivity | SPEC.md (Demand-vs-cap diagnostic §) | demand-vs-cap ratio; <10x standing bar on trailing-24h; cap-blocked-but-EV-clearing counts logged per cycle |
| X-identity / X-self-governance / X-capacity-check | desks/X.md | exploration mandate (2026-10-05 recharter); unscored quarantine; liquidity honesty |
| Q-identity / Q-self-governance | desks/Q.md | sports-quant mandate; model-versioned entry bar |
| C-identity / C-self-governance | desks/C.md | sentiment-fade mandate; documented-extreme entry bar |
| R-identity / R-self-governance / R-scoring / R-prevented-loss-ledger | desks/R.md | red-team mandate; kill-precision scoring; prevented-loss ledger |
| MANAGER-role / MANAGER-hourly-loop / MANAGER-report / MANAGER-escalate / MANAGER-learning-protocol | desks/MANAGER.md | floor operation; synthesis; escalation; cross-desk learning |
| FOUNDRY-governors / FOUNDRY-spawn-checklist | desks/FOUNDRY.md | context & scoring-bandwidth governors; breeding procedure |

Attribution procedure (runs on `propose-*` / `escalate`, owned by the 07:11
loop's calibration step, judged by K3N1):
1. **Evidence:** read `brier.py --json` `trade_panel`; filter
   `in_decay_window`; sort by `weight × brier` descending — the worst
   weighted contributors first. Each entry carries desk, market, side, p,
   outcome, thesis (truncated), and provenance.
2. **Read the failures:** open the top contributors' theses (full text in
   PAPER.md via the market slug). Ask per trade: which charter block's rule
   produced this p, this entry, this exit? A mispriced p-estimate points at
   the entry-bar block; repeated oversize at the sizing block; faded edges
   that weren't edges at the mandate block.
3. **Rule out non-prompt causes first:** regime shift (the world changed —
   check NEWS.md for dated breaks inside the decay window), variance (eff_n
   near the 15 floor — the SE note applies), bad luck clustering (a few
   high-brier trades dominating a thin panel). If the evidence doesn't
   isolate a block, the proposal says so — "no attributable block" is a
   valid finding, and it defaults to `watch`.
4. **Proposal format:** status, direction, the numbers (lifetime vs decayed,
   eff_n, n), the candidate block ID(s), the cited trade slugs, and the
   proposed block-targeted diff. Immutable constraints (EV bands, sizing
   caps, fill rules, R review — the Guardrails) are never proposal targets.
5. **Authority:** the loop proposes; K3N1 judges and applies. Every applied
   change is logged (block ID, before/after, evidence cited, date) in the
   charter's history or the daily log.
6. **Local models as log parsers:** a local model may assist step 2 at
   scale, but it reads the structured trade panel and CITES trade slugs —
   it is a parser, never a narrator and never a rewriter. Its output is a
   proposal input; K3N1 remains the only compiler.

**Extended by:** the Self-improvement promotion pipeline below
(audit-resolved 2026-09-24) — structured proposal schema, two-tier evidence
bar (mechanical vs judgment), and the code-enforced promote gate. The
procedure above remains the manual-first path for the first hand-worked
attributions.

## Self-improvement promotion pipeline (audit-resolved 2026-09-24 — outside review + K3N1 response)

**Design principle:** self-improvement is a structural pipeline with
code-enforced gates, not a prompt that says "reflect on your losses and do
better." The enforcement hierarchy applies unchanged: CODE > STRUCTURAL >
mechanical-prose > judgment-prose. Manual-first posture stands throughout —
no wiring until hand-worked baselines exist.

**Three layers, kept separate:**
1. **Attribution** — per-desk, per-signal-type, decay-weighted,
   sample-size-gated. Produces evidence, never changes.
2. **Proposal generation** — LLM-driven, creative. Output is a *diff
   proposal file*, never a live write.
3. **Promotion** — the actual gate. Code-enforced criteria; a proposal
   becomes live only by passing the promote script.

### Layer 1 — Attribution (mechanical core; ships BEFORE the statistical gate)

- **Binding-constraint logging (receipt fields, in `book_trade.py`):**
  every booking receipt records `entry_path` (S: `m-gate-clearer` |
  `near-gate-add`; F: origination slot #; Q: model version),
  `binding_cap` (`book-cap` | `kelly`), and `ev_at_central`. Sequencing
  rule: these fields land before the promote gate is built — no
  statistical gate on top of an unlogged mapping.
- **Mechanical mapping rule:** p-miss → the desk's entry-bar block; size
  anomaly → the sizing block; exit-timing loss → the exit-rule block.
  These follow from the logged binding constraints, not from judgment.
- **Labeled residual:** anything the mechanical rule can't map stays
  judgment, and every proposal carries `attribution_basis: mechanical |
  judgment` per cited block — the gate knows which part is validated and
  which isn't. "No attributable block" remains a valid finding (defaults
  to `watch`).
- **Panels:** `brier.py` emits per-(desk, block/signal) decay panels as
  JSON (the attribution input), not just per-desk.
- **Half-life, stated plainly:** the 21-day half-life is a starting
  guess, never tuned. Until it is: robustness check in code — panels
  computed at 14d/21d/42d, and a propose badge requires agreement across
  ≥2 of 3, so no single arbitrary half-life can trigger learning alone.
  Tuning against the golden set (which half-life best separates known
  calibration shifts from noise) happens once the golden set exists.

### Layer 2 — Proposal generation (structured diffs, never live writes)

- **Schema:** `proposals/pending/<id>.json` —
  `{proposal_id, ts_cdt, status, direction, numbers{lifetime, decayed,
  eff_n, n}, block_ids[], trade_slugs[], attribution_basis,
  diff (unified, block-targeted), expiry_date, evidence_pointers[],
  success_metric}`.
- **Validator** (small, readable, Gabe-reviewed before anything flows
  through it): schema valid; every block ID exists in
  `hidden_files/block_registry.json` **and** has status `open`; the diff
  touches no locked/Guardrail block (EV bands, sizing, fill rules,
  R review, kill switch, real-money path); single-block: the diff touches
  exactly one open block — multi-block proposals are rejected; decompose
  into sequenced single-block proposals, each gated independently, so
  attribution and the FDR family stay strictly per-block with no extra
  machinery; `success_metric` is realized calibration (Brier vs outcomes) — proxy metrics (EV-gate hit rate,
  Kelly-sizing accuracy) are rejected; `expiry_date` present. Rejected →
  appended to `proposals/rejected.jsonl`, never applied. Rejection, never
  clipping (same rule as the proposer contract).
- **The gate list itself is never a valid proposal target:** the
  validator rejects it on sight and logs an `EVENT:` line. Changes to
  promotion criteria are Gabe-only, permanently — the same way the
  real-money key never leaves his hands.
- **K3N1 remains the only compiler:** no agent writes charters directly;
  applied diffs are hand-applied after the gate clears, logged (block ID,
  before/after, evidence, date).

### Layer 3 — Promotion (the gate; `promote`, the sibling of `book_trade.py`)

Checks run in order; any failure rejects (exit non-zero), never queues:
1. **Sample size:** `attribution_basis=mechanical` → eff_n ≥ 15;
   `=judgment` → eff_n ≥ 30.
2. **Significance vs null:** mechanical → |decayed − lifetime| ≥ 0.05;
   judgment → ≥ 0.07 (≈2 SE at eff_n=30 — the band tightens as SE
   shrinks, so the bar gets harder with n and can't be gamed by padding
   weak-signal trades). Never "PnL went up."
3. **Multiple comparisons:** Benjamini-Hochberg FDR at q=0.10 across the
   per-(desk, block) test family — computed from `block_registry.json`
   at runtime, never a hardcoded count — per evaluation.
4. **Rate cap:** ≤2 promotions/week (mechanical backstop).
5. **Held-out replay:** the proposed change must improve-or-hold the
   golden slice-B panel on trades the proposer never saw. Holdout
   trade/market IDs are committed to `hidden_files/holdout_ids.txt`
   *before* their theses are written anywhere retrievable; `rag.py`'s
   indexer skips chunks matching holdout IDs **at index time** (the
   drafting worker's only retrieval path is that index); the golden
   artifact file itself is excluded from the corpus.
6. **Expiry:** every promoted rule carries an expiry/re-validation date
   (≤ one 30d epoch); rules whose supporting trades age out of the decay
   window are re-flagged automatically.
7. **Authority:** anything touching the real-money path (M blocks, EV
   gate, sizing, kill switch) → Gabe's sign-off, always.
   `attribution_basis=judgment` → Gabe's sign-off, always — no
   auto-promote path exists for judgment-basis proposals; without a
   recorded sign-off the script rejects, it doesn't queue.

**Auto-fire (no human invocation in the path):** `promote-watch`
minutely cron scans `proposals/pending/` for files lacking a receipt in
`proposals/decided/`, runs promote on each, and writes a heartbeat to
`hidden_files/promote_watcher.heartbeat` every tick. The hourly brain's
step-0 verification checks promote-watch run recency **and** heartbeat
freshness (>10 min stale → `EVENT:` + structural flag in the mandatory
final message → K3N1 messages Gabe; structural failures are a contact
trigger). The charter-integrity audit runs in the same step: any charter
block edit without a matching promote receipt is flagged (same pattern
as `book_trade.py audit`). Dark pipeline caught by heartbeat; rogue
writes caught by audit.

**Gate enforcement register (this pipeline):** CODE = sample /
significance / FDR / rate-cap / holdout-exclusion / reject-not-queue /
auto-fire / charter-audit; STRUCTURAL = real-money separation, Gabe's
sign-off on judgment-basis + real-money-path proposals, Gabe owns the
gate list permanently; PROMPT = none — that is the point.

### Block registry (the living ledger)

`hidden_files/block_registry.json` — every block ID, its file, what it
governs, its status (`open` | `locked` | `evidence` | `cosmetic`), and a
change log. The validator reads it; any count or status change without a
logged entry is flagged by the charter-integrity audit. Source of truth is the file itself —
read counts from `counts`, never from prose. At last recount 2026-09-24: **59 entries**:
**23 open** (22 desk blocks + SPEC.md Funnel-selectivity), **15 locked**
(Guardrail/structural), **14 cosmetic** + **7 evidence** (decision logs,
strengths/weaknesses, MANAGER-history). Every entry carries `last_reviewed` and
`provenance`; cosmetic entries additionally carry `revisit_trigger` (next golden-set refresh,
or 90d stale-route to reaffirm/revise/retire, whichever first) so "cosmetic" can't become a
one-way door to being forgotten. Stale entries (>30d without review, or past their trigger)
are filed as judgment-basis proposals in `proposals/pending/` for manual action — never
auto-resolved by heuristic. The open set is the learning
surface, in writing — "we have a validator" can never imply a bigger one.

### Golden eval set (one build, two gates, no double-duty)

`golden/v1/`, `v2/`, … — old versions retained for comparability.
Refresh cadence: every 30-day epoch, or on a dated regime break,
whichever comes first. Two slices built in one pass from **disjoint
trade sets**: slice A = parser grading (citation agreement on
hand-worked attributions); slice B = promotion replay (held-out scored
trades). v2+ staggers the slices' **time windows**, not just their trade
IDs (a one-pass split shares one window's blind spots).

### Bandit scope (structural fact, not intention)

Desk-weight reallocation touches paper notionals and attention
allocation (funnel candidate assignment) only. The real-money authority
chain — gates, sizing, caps, the key paste, the kill switch — is
Guardrail-tier and excluded from the validator's allowlist. No proposal
targeting it can pass.

### Failure-mode register

- **Goodhart on our own eval** → score realized calibration (Brier vs
  outcomes), never proxies; the validator rejects proxy-metric
  proposals; p-honesty enforced by scoring, not code (proposer contract).
- **Non-stationarity** → every promoted rule carries expiry/re-validation;
  decay aging re-flags; the pre-registration kill-condition discipline
  extends from hypotheses to charter diffs.
- **Small-n desk reallocation** → Bayesian bandit with a strong prior on
  no-change (shrinkage toward equal weights); weight-change proposals
  need eff_n + significance-vs-null before reaching K3N1.
- **Self-modification of the modifier** → promotion-criteria changes are
  Gabe-only, permanently; gate-targeting proposals rejected +
  `EVENT:`-logged.

### Build order

1. Binding-constraint receipt fields → 2. `block_registry.json` +
   validator → 3. holdout exclusion in `rag.py` → 4. golden v1 at the
   first propose badge → 5. promote script + watcher + charter audit.
   Manual-first throughout: each gate clears on hand-worked baselines
   before anything wires up.

## Paper-universe rule (decided 2026-09-24, 07:11 deep loop)

Book M (the mirror) may only book markets discoverable on polymarket.us —
what the real account could actually take. A mirror that books markets the
account can't trade is fiction. S and F range across .com as simulation/R&D.

## Desk X — "Empire" — the exploration account (added 2026-09-24 ~08:08 CDT, Gabe's order; rechartered 2026-10-05 to Gabe's stated original intention: an account with a lot of money where we find what works)

$1,000,000 paper, flat $20,000/trade (2%). X originates freely across markets, thesis families, and horizons — including everything the gated desks reject — to produce **quantified understanding of the market**. We are an information firm: X's product is priced information, not P&L. No EV/mikiri gate binds X (the gate is the assumed-risk model under test); the honesty gates bind (price units, settled universe, thesis schema, driver taxonomy, ledger integrity). Family-correlation and driver-concentration caps do not bind X — driver and family are still declared for the research record. Every exploration pre-registers its quantitative question and kill condition; results feed the shared data plane. A thesis family that demonstrates edge graduates upward through the normal gates. **Unscored sandbox:** excluded from the calibration log, Brier scoring, oversize-flag math, and any real-money inference. Quarantined ledger in PAPER.md. Capacity checks via the `shadow` subcommand retained as a secondary function.

### X thesis-family lesion protocol (added 2026-10-06 — the macro-ResNet audit)
Family-correlation and driver-concentration caps do not bind X, so redundancy cannot be gated — it must be **measured**. A desk without correlation gates is susceptible to becoming an ensemble in a tower's clothes: many theses, one disguised bet. The lesion protocol proves X's internal depth is capacity, not redundant voting.
- **Method:** retrospective ablation over resolved positions only. For each thesis family F, recompute book-level metrics with F included vs excluded: realized ROI, hit-rate-vs-entry-price (calibration-in-the-small), and F's P&L correlation with rest-of-book. Plus a pairwise family-P&L correlation matrix each sweep — if all families' errors correlate, the firm holds one macro bet, not a portfolio. **Resolved set (added 2026-10-06, pre-data):** exit-closed rows (close_action=exit) enter at realized P&L alongside settle rows — excluding exits would survivorship-bias family ROI. Every row is tagged `exit` or `settle`; the report shows per-family exit/settle counts and P&L split, so a family can't look redundant or strong because of how positions were closed rather than what the theses were worth. An exit-majority REDUNDANT flag carries an exit-quality caveat — annotation-only, it does not change the flag's trip conditions.
- **Sparse weeks (added 2026-10-06, pre-data):** weekly P&L buckets are built only from weeks with ≥1 resolved trade per family; "overlapping" means weeks where *both* families traded. Non-trading weeks are excluded, never zero-filled — zero-filling would manufacture correlation among inactive weeks. An 8-bucket overlap therefore means 8 weeks of joint activity, not 8 calendar weeks.
- **Cadence (decided 2026-10-06):** (1) **event-driven** — recompute whenever any family crosses a multiple of 10 new resolutions (cheap ledger recompute; runs in the 07:11 deep loop, the hourly cycle stays lean); (2) **calendar backstop** — full cross-family sweep every 14 days regardless of counts, small-n uncertainty flagged, never overclaimed; (3) **pre-adjudication gate** — mandatory full lesion report before the Q4 kill verdict, because eff_n ≥ 15 could be satisfied by one hot family and the adjudication must know whether the *firm* has edge or one family does.
- **Redundancy flag (pre-registered before the first run — bars are never re-tuned after data is seen):** excluding F changes book ROI by <1pt AND F's standalone calibration shows no edge AND F's P&L correlates >0.7 with rest-of-book → flag F redundant; pause new originations in F pending K3N1 review. **Correlation floor (added 2026-10-06, pre-data):** the >0.7 clause evaluates only with ≥8 overlapping weekly P&L buckets; with 4–7 buckets the matrix is computed but the clause reports insufficient-data and REDUNDANT cannot trip — a correlation on a handful of resolutions is noise, not signal. **Why 8:** at n=8, r≈0.71 is the two-sided p=0.05 significance line for Pearson correlation, so the 0.7 threshold sits exactly at the edge of statistical significance — below 8 weeks a 0.7 correlation wouldn't clear noise anyway. The floor is principled, not round-numbered. **Pause deadline (added 2026-10-06, pre-data):** a paused family gets a K3N1 review within 14 days of the flag; the review clears the flag or extends the pause with a dated reason and a next review date. A pause without a deadline starves its own future resolutions and gets stuck paused. **Extension cap (added 2026-10-06, pre-data):** at most two extensions; the third review escalates to Gabe — he clears, extends with his dated authorization, or retires the family. K3N1 cannot rubber-stamp its own pause indefinitely.
- **Scope honesty:** lesioning measures redundancy, not edge. A non-redundant family can still be negative-EV; the kill condition handles that separately. Do not conflate the two verdicts. The ablation is also **counterfactual, not a true lesion**: it replays history without the family while ignoring sizing and bankroll interactions (flat $20k/trade assumed, no cross-family capital reallocation) — it estimates what the book's P&L would have looked like, not what the book would have done.
- **Owner:** K3N1 as auditor (unshared-skull rule — the Executor never grades its own homework). Results to the X desk log; flags surface in the daily standup.

## Local-model fine-tuning policy (decided 2026-10-06 — pre-registered before any candidate task)

No general "operate Nightwatch" fine-tune: trading judgment has noisy, delayed, sparse labels — little clean signal to train on. A narrow task-specific fine-tune is considered only when all of the following hold, measured before training:
- **Demonstrably weak (the number):** on a held-out eval set of ≥200 hand-labeled examples, the base model's error rate is ≥20% AND the fine-tuned candidate beats it by ≥10 absolute percentage points on the point estimate AND the 95% paired bootstrap CI (10k resamples) on the error-rate difference has its lower bound ≥5pt. At n=200 the SE on the difference is ~3–4pt, so a bare 10pt point estimate sits near the noise floor — the interval requirement is what makes the improvement real, not the point estimate. McNemar as a cross-check. Both bars pre-registered; the 20% floor means the task is handled well enough to leave alone, the 10pt/5pt bars mean the gain is worth the maintenance burden.
- **Labor accounting:** 200 blind labels at ~5 min each is ~17 hours — but labels accumulate prospectively inside normal operation (blind labels recorded during regular triage/review), not as a separate project: ≈1.3 hrs/week over a 90-day window. If a task can't supply 200 labels that way, it doesn't have the data density to justify a fine-tune.
- **Stakes exceptions (the loophole, capped):** a lower bar for a specific high-stakes task must be logged as a judgment-log entry with its justification BEFORE the first eval example is labeled. Hard floors: base-error bar never below 10%, point-improvement never below 5pt, CI lower bound must still exclude 0 (the improvement has to be real, even if smaller), eval minimum stays 200. An exception that can't clear its own floors is not an exception.
- **Eval from outside the training data:** eval examples come from a time window disjoint from training, labeled blind (without seeing model outputs), and before outcomes are known when the task is outcome-sensitive. An eval drawn from the training window measures fit to those weeks, not generalization — the sparse-label problem applies to the eval as much as to training.
- **Revisit trigger:** re-evaluate every 90 days or when 200 new hand-labeled examples accumulate for a task, whichever comes first. The standing "no" is decided on evidence, not inertia.

## Judgment decision log (added 2026-10-06 — the label pipeline)

Mechanical gates can't cover calibration overrides, kill adjudications, doctrine decisions, or gate changes — those stay with K3N1. The only route to training labels for judgment is logging the judgments with outcomes attached. Append-only log: `hidden_files/judgment_log.jsonl`. Schema per row: decision_id, ts_cdt, category (calibration-override / kill-adjudication / doctrine-decision / gate-change / sizing-override / other), decision, alternatives_rejected, reasons (≤5 lines), **confidence** (0–1: my credence the decision is right, stated at log time), **wrong_if (mandatory)** — the falsification criterion with a date: what observable outcome proves this decision wrong. A judgment without a pre-stated wrong_if is not loggable; without it, outcome attachment becomes retro-justification. outcome, outcome_ts, verdict ∈ {correct, incorrect, unresolved} — attached at resolution, never reconstructed from memory.
- Logged at decision time, before outcomes are known. **What gets logged (Goodhart guard):** any decision that (a) authorizes or blocks a trade, (b) changes a registered threshold or bar, (c) pauses/retires a desk or family, or (d) commits the firm to a dated future action is logged by default — not at my discretion. The 07:11 loop body requires a judgment-log entry as part of registering any new bar. Monthly review reports logged-vs-eligible counts; a month with eligible-but-unlogged decisions is itself a finding.
- **Calibration, not just hit rate:** monthly scoring uses a proper scoring rule — Brier score on stated confidence vs outcome — and bins judgments by stated confidence for the calibration curve, public like everything else. A proper rule rewards honest confidence: correct at 0.95 outscores correct at 0.55, and calibration is judged across the set (at 0.55 you should be right ~55% of the time). Safe calls logged at 0.85–0.9 that always land earn little and don't move the curve. Two limits, stated plainly: an empty bin shows avoidance of a confidence range, not proof of ducking hard judgments; and with ~3–8 entries/month, per-bin calibration is uninformative until roughly 30+ resolved entries — until then the log is a record, not a verdict.
- **Arrival rate and the empty 90 days:** loggable judgments arrive at roughly 3–8/month at the firm's actual cadence, and outcomes take weeks to attach — at that rate 50 outcome-attached decisions arrives in roughly 6–17 months: about a year, with wide error bars. The 90-day revisit therefore usually has little resolved data; when it has none, it still produces a dated verdict ("no new evidence — standing decision holds"), itself logged as a jd entry with its own wrong_if. "No, again" by silence is not an option.
- **Label trigger:** at 50 outcome-attached decisions, assess whether the labels are clean and dense enough to support any fine-tune experiment under the policy above. Until then the log is an accountability instrument, not a dataset.

## Desk foundry (added 2026-09-24 ~08:12 CDT — Gabe: "lots of iterative rats running out testing any # of paths")

K3N1 breeds runner desks from `desks/TEMPLATE.md`; procedure in `desks/FOUNDRY.md`.
Governors (Gabe's law — context is the budget): (1) context — every desk's
output must be read and synthesized, so handoffs stay ≤15 lines and the brain
reads ledgers, not charters; (2) scoring bandwidth — no desk without a ledger
and a scoring hook. Every new rat must own a differentiation axis (source,
domain, thesis type, horizon). Theses flow Q/C/F → M → S → X (graduation
upward only); R red-teams every thesis pre-booking (advisory, never a veto).
Living rats: M, S, F, X, Q, C, R.

## Audit resolutions (2026-09-24 ~08:50 CDT — Gabe's punch list, items 1–9 + structuring notes A–E)

### Authority: the Gabe contact channel (absolute)
K3N1 (the main agent) is the ONLY layer that contacts Gabe. Every Gabe-facing
output — standup text, dashboard content, hard-stop alerts, structural flags,
fire lines, real-money credential requests — is authored and sent by K3N1.
Cron workers, hooks, and sub-processes NEVER message Gabe; they write files
(STATUS.md, hidden_files/real_money_request.json, the mandatory final-message
handoff). K3N1 composes from those files. No bypasses: the hard-stop alert and
structural-risk flags flow through the same channel.

### Escalation threshold: the lost-handoff rule (formal)
4 consecutive null `result_summary` on `polymarket-market-watch` = structural
escalation (suspected relay degradation). Evaluated by K3N1 at each hourly
synthesis via the disk-verify (STATUS.md mtime + worker_state.json
last_run.id). On trigger: K3N1 notifies Gabe as a structural failure + a
LESSONS.md entry is written. Any 4-in-a-row counts — no time expiry, no reset
window. This supersedes the old "two consecutive traceless" bar: nulls are
counted whether the run was traceless (no disk traces) or a lost handoff
(fresh traces, dropped delivery).

### Thesis lifecycle & the R-review gate
Every thesis carries R-review state: `R_REVIEW_PENDING` → `R_REVIEW_COMPLETE`.
- Paper trades execute IMMEDIATELY — no R wait. Paper booking is never blocked.
- NO thesis may be nominated M→K3N1 for real money until R has issued a kill
  note on it (R runs one cycle behind, so the review lands the next cycle).
  The synthesis step checks every real-money nomination for pending/incomplete
  R review and blocks the nomination — not the trade.
- A skipped-R-review event (nomination blocked) is logged to LESSONS.md
  prefixed `EVENT:` with cycle_id and timestamp.
- **R overdue (stuck R_PENDING):** R gets one cycle to review (its lag). A
  thesis still `R_REVIEW_PENDING` after 2 cycles is `R_OVERDUE` — its own
  alert lane, distinct from the general staleness/escalation counters. On
  detection the synthesis step logs `EVENT: R_OVERDUE <thesis> <age-cycles>`
  to LESSONS.md, carries one line in the final message, and flags it in
  STATUS.md. The block stands (safe direction — no money moves); nothing
  auto-unblocks. 3 R_OVERDUE events in a rolling 7 days → LESSONS.md
  reliability entry and an R prompt review by K3N1. A single thesis overdue
  5+ cycles → structural flag in the final message (R's branch may be dead;
  K3N1 evaluates).

### Real-money gate: a separate module
The real-money path is structurally separate from paper synthesis — a separate
step (SKILL.md §5), not a conditional branch inside paper logic. A bug in
paper-book logic cannot reach the credential-request step because that step
does not exist in the paper path: it exists ONLY in K3N1 main-agent turns,
never in worker synthesis. Workers prepare the package
(hidden_files/real_money_request.json + final-message flag); K3N1 authors the
Gabe message and runs the authenticated window.
The 1–4 week dated-catalyst requirement on M's entry bar is load-bearing for
the credential-latency model: it is what makes the paste latency acceptable.
Do not loosen it without revisiting the credential model with Gabe.

### Dispatch layer, barrier, single-writer synthesis
- Snapshot-then-fan-out: the coordinator builds an immutable cycle snapshot
  (prices, watchlist, caches, RAG hits, cycle_id, timestamp) and hands it to
  all desks. No desk mutates shared state mid-turn — desks return structured
  decision objects (DESK/TRADE/PASS), never write shared files.
- Per-dispatch timeout: 10 minutes. On timeout, log a missed cycle for that
  desk (LESSONS.md, `EVENT:` prefix) and proceed with whatever returned.
- Quantum enforced at dispatch: inputs truncated to ≤5 candidates; outputs
  >10 lines per desk rejected as invalid and logged.
- Barrier wait = "all dispatched desks for this cycle_id have returned or
  timed out" — never a fixed sleep. R and X are excluded from the wait (R:
  one-cycle-lag branch; X: post-barrier booking).
- Single writer: only the synthesis step writes STATUS.md, WATCHLIST.json,
  PAPER.md, TRADES.md.

### Observability: staleness and the event log
- STATUS.md header carries an explicit `last_updated` timestamp. Stale if
  older than 90 minutes past the :48 hourly mark. Fresh timestamp + no news =
  healthy silence; stale timestamp = dead process. No human needed to tell
  the difference.
- Structured event log: every desk timeout, output truncation, and
  skipped-R-review gets a LESSONS.md line prefixed `EVENT:` with cycle_id and
  timestamp. These feed the weekly blackboard synthesis.

### S correlation clusters (programmatic)
A correlation cluster = positions sharing (a) the same event slug family, OR
(b) the same market category AND resolution dates within 7 days, OR (c) the
same directional macro driver tag. Rule: max ONE open position per cluster; a
new candidate in an occupied cluster is rejected unless the existing position
closes. S tags every candidate with `event_family`, `category`,
`resolution_date`, `driver_tag` (charter: desks/S.md). The system-wide rule
(correlated markets = one risk slot across all books) stands; this makes S's
check programmable.

### R kill-precision scoring (resolution-graded)
At resolution, every reviewed thesis is graded against R's kill-note:
| Kill | Thesis outcome | Score |
|---|---|---|
| HARD | lost | 1.0 |
| HARD | won | 0.0 |
| SOFT | lost | 0.5 |
| SOFT | won | 0.0 |
| MISS | lost | 0.0 |
| MISS | won | 1.0 |
Kill precision = sum / total reviewed. Graded at resolution from the ledger —
objective, no peer review, no hindsight re-grading. Ledger in desks/R.md.
Monthly review: precision < 50% on 10+ graded kills → R's prompt rewritten.

**Prevented-loss shadow ledger (R's invisible best calls, made visible).**
Kill precision only scores booked theses — a HARD kill that stops a trade
from ever happening has no settled outcome in the denominator. Not
acceptable to leave invisible: every thesis that R kills (HARD or SOFT)
and that is NOT booked within 2 cycles enters the prevented ledger in
desks/R.md. At the thesis's stated horizon or market resolution (whichever
comes first), the kill is shadow-graded against what would have happened:
HARD + would-have-lost (resolved against the thesis side, or price moved
≥10¢ adverse = would have hit the mechanical exit) = 1.0; HARD +
would-have-won = 0.0; SOFT + would-have-lost = 0.5; SOFT + would-have-won
= 0.0. Reported as a SEPARATE number — "prevented tally (shadow-graded)" —
never mixed into kill precision's denominator. Honest caveat: shadow
grading is noisier than grading a booked trade (no fill, no adverse touch),
which is exactly why it stays its own tally. The monthly review reads both.

### Honest fills: book-walk execution (replaces the haircut 2026-10-06)
Paper entries fill against the LIVE order book at booking time — never at an
assumed price. The worker's `--price` is the LIMIT; `book_trade.py` walks the
book (`bin/fill_engine.py`) and executes at VWAP. Slippage therefore grows
with size by construction: a $1 fill and a $2,000 fill do not get the same
treatment. Each clip is additionally capped at the depth the book absorbs
within 1¢ of the touch — volume-independent and moment-specific (daily volume
says how much trades in a day, not how much you can take at one moment).

- **Fail-closed entries:** no depth snapshot → the booking is REFUSED
  (`honest-fill`), logged in the rejection log. An assumed fill is an
  invented fill. (The old `assumed-fill` tag is retired for entries.)
  2026-10-07 repair: the .com snapshot path was dead since the 10-06
  recharter — gamma-api 403s the default urllib User-Agent (now sent) and
  returns `clobTokenIds` as a JSON-encoded string (now parsed; `tids[0]`
  on the raw string built a garbage token URL → CLOB 404). All .com
  entries failed closed during the outage — no invented fills, but the
  spend directive was silently starved. Lesson: stubbed tests never
  exercise the real gamma schema; a transport repair needs a live
  smoke check, not just the suite.
- **Fail-open exits:** loss-capping must never be blocked by a dark feed. The
  exit walks the bid side when a snapshot exists; otherwise it falls back to
  the worker/poller price, tagged `exit_basis: unverifiable`.
- **Taker fees modeled** per the venue's published schedule (checked
  2026-10-06; `FEE_SCHEDULE_RECHECK = "2027-01-04"` in fill_engine.py):
  `fee = shares × rate × p × (1−p)` — .com by category (crypto 0.07, sports
  0.05, econ/culture/weather/other 0.05, finance/politics/tech/mentions 0.04,
  geopolitics/world 0), .us 0.0695. Unknown category → fee logged as
  explicitly-zero (`fee_unknown: true`), never silently-zero. P&L is net of
  entry + exit fees, at settlement and at exit.
- **Receipt fields:** `price_c`/`size_usd` are EXECUTED (VWAP/filled);
  `attempted_usd`, `unfilled_usd`, `limit_c`, `fee_usd`, `fee_rate`,
  `fee_category`, `depth_1c_usd`, `fill_venue` recorded alongside.
- **X breadth (2026-10-06, Gabe's "breadth first"):** X books a $2,000 target
  clip (0.2% of the $1M paper bankroll), depth-capped by the walk — many
  small positions across many markets, because resolutions per week are the
  scarce input. The $20k flat is retired: it answered neither "what survives
  at size?" (the haircut/cap never measured depth) nor "what works?" (a few
  big clips resolve slowly and noisily). Capacity is revisited later as a
  pre-registered experiment on whatever desk shows an edge, with the walk
  already in place. The demand-vs-cap diagnostic (<10x trailing-24h) stays
  as a watcher, not the booking gate.

### X capacity-check report surface
X's capacity checks live in a dedicated section of desks/X.md — never
commingled with the DESK/TRADE/PASS decision objects that feed synthesis. The
capacity question ("would this edge survive $20k?") must not influence market
prioritization through a side channel.

## Context budget (added 2026-09-24 ~05:00 CDT — Gabe's directive)Context window and Gabe's tokens are the operating cost. The hourly brain runs lean:
- **Skill, not body:** the loop procedure lives in `~/workspace/skills/nightwatch-market-watch/SKILL.md` (self-updating via `PROCEDURE_NOTES.md`); cron bodies are pointers holding only run-specific rules.
- **Bounded working set:** `hidden_files/worker_state.json` (positions, recent decisions capped at 12, funnel counts, news watermark) is read first; full `PAPER.md`/desk logs/`NEWS.md`/`LESSONS.md` are never re-read to recover what it holds.
- **Cache map with TTLs:** prices (90s hook cache), market metadata (static, on WATCHLIST change), settled outcomes (immutable, never re-queried), funnel candidates (6h), news (watermark delta), cron statuses (hourly snapshot). Recompute only on TTL expiry, structural change, or explicit invalidation.
- **RAG before full reads:** `skills/nightwatch-market-watch/bin/rag.py` (local SQLite FTS5 over the corpus — goal files, desk charters, sync board, and reading-program notes) for long-tail questions; `tail -40` for `NEWS.md`/`LESSONS.md`.
- **Caps:** final report ≤15 lines; `STATUS.md` ≤25 lines; handoffs carry decisions, not narration.
- **Shared data plane (2026-09-24 ~08:16 CDT — Gabe: don't multiply usage spawning rats):** prices, news, funnel candidates, and market metadata are fetched ONCE per cycle into the shared caches; all desks read the same caches and the same RAG index (`desks/*.md` auto-globbed — new charters index themselves). Per-desk re-fetching of shared data is a spec violation. A desk needing uncached data extends the fetch phase (TTL/watermark permitting), never goes around it.
- **Synchronous fan-out (2026-09-24 ~08:23 CDT — Gabe: scale/quantize the brain):** the hourly brain is a coordinator — fetch phase → one runner subagent per litter dispatched synchronously → barrier → synthesis over bounded outputs. Fixed quantum per desk per cycle (≤5 candidates in, ≤10-line decision block out). R red-teams on a one-cycle lag; X books after the barrier. Sequential desk chains are banned — that's how a growing mischief becomes skim.
- Relocating text body→skill saves nothing by itself — the savings come from shorter total instructions, bounded reads, cache-first data, and capped outputs.
- **Local inference tier (added 2026-09-29 — Gabe's directive: full hardware use, $0 marginal cost):** K3N1 runs on Gabe's Windows desktop (`gdesk`, Tailscale (address redacted for publication)) via the runtime TCP proxy; Ollama serves `qwen2.5:14b` (workhorse — benched 10/10 reliability, triage/summarize/extract graded clean). Parked models deleted after soaks (gemma4:26b verbose, qwen2.5:32b same quality at 3–5x latency, Hermes-4 format violations — 36GB reclaimed); nomic-embed-text remains for vector RAG. Routing policy: local tier handles only bounded, mechanical, source-verifiable work (news triage, summarization, extraction); frontier retains all decisions, calibration, doctrine, and money gates. Every local output is advisory and verified against its source before use. `keep_alive 2h` (effectively resident while hourly cycles run; his Ollama rejects `-1`). If `gdesk`/Ollama is unreachable or the GPU is contended, the tier yields to the pure-CPU extractive fallback and logs the heartbeat path — Nightwatch never breaks or retry-loops on it. Spec: `hidden_files/local_orchestration.md`; client `bin/ollama_local.py`; soak gate: 20 consecutive summaries with zero factual contradictions before stage-2 admission (PASSED 2026-09-29 — summarization ADMITTED as LIGHT_BRIEF 2c, advisory/verify-before-use). The verbalized-confidence gate (0.85) is DROPPED — known-perforated (the observed qualifier-loss failure scored 0.90); the mechanical gate (exit 2) decides. Full SSH access to gdesk live (key and workspace paths redacted for publication).
- **Local-tier audit CLOSED 2026-09-29 (reforms 1–6):** span contract + mechanical gate (verbatim spans, qualifier regex, exit 2), 15 sealed canaries pre-flight, cryptographic pins (4 prompts + 2 gate schemas + model digest + DIGEST_SCHEMA; `repin.py --reason` ceremony), circuit breaker (2 consecutive transport failures / 3 consecutive faults / 50%-of-10 density; trip-refusals excluded), drift metrics (advisory-only, pinned baseline, deep-loop LESSONS.md), CPU fallback (extractive baseline, distinct provenance). **Exception-only digest (reform 6, capstone):** the frontier never reads raw local-tier output — Channel A mechanical verification use only; Channel B `bin/exception_digest.py` renders heartbeat faults + trip files + drift advisories into the pinned fixed-vocabulary schema (deep-loop only; LESSONS.md digest-only; 30-day ledger freeform + isolated). Contract: `files/local-tier-integration-contract.md`. 199/199 across 9 test suites.

## Demand-vs-cap diagnostic (added 2026-09-24 — Gabe's directive, from backtest cycles 2–3)
- **Definition.** demand = evaluations that cleared the desk's EV floor but were blocked by a cap (per-desk origination cap or open-position cap); cap = booked trades that cycle. Ratio = demand / booked, reported as Nx per desk. (Backtest name for the same number: cap ratio = cap-bound PASS rows / booked.)
- **Logging.** The hourly brain's synthesis step writes `funnel.cap_blocked_ev_clear` (per desk) and `funnel.booked` (per desk) into `hidden_files/worker_state.json` every cycle, alongside the existing funnel counts. Additive keys — no schema break.
- **Aggregation.** Caps reset daily, so the standing bar evaluates on the **trailing-24h aggregate per desk** (sums of the per-cycle logged values). Per-cycle values are inputs, not verdicts. Zero-booking windows log the raw `demand:booked` pair (e.g. `3:0`); a `0:0` window (no demand, no bookings) is a quiet-model signal, not a 0x ratio.
- **Rendering.** The STATUS.md heartbeat and the dashboard render surface the trailing-24h ratio per desk (one line / one pill). A backtest summary without the cap-ratio column is incomplete — the same bar holds for live renders.
- **Reading.** High ratio (≥10x) with weak or zero edge = an indiscriminate model being loss-limited by the cap, not a selective edge. Standing red flag, not a one-cycle curiosity. Response: fix selectivity (entry bar, filters), never expand size on a high ratio.
- **Standing bar.** <10x per desk on trailing-24h. Breaches don't auto-halt anything — they route to the desk's decision log and the next 07:11 calibration review. Tighten or loosen after a few weeks of live history, not before.
- **Market-capacity reference (measured 2026-10-02, N1K3 T17 — full 1.028B-row parquet, 1,331 days, raw usd_amount per UTC day).** This is the ocean the desks swim in — do NOT confuse with the per-desk demand/booked ratio above; different instrument. p50 $8.97M/day, mean $28.37M/day (3.2× median — highly right-skewed), p90 $107.7M, p99 $165.9M, max $240.8M (election-cycle peaks). Use: sanity-checking dollar cap sizes and "can the market absorb this" questions. N1K3's recommendation (anchor a volume bar to 10× trailing-30d median, recomputed monthly) is adopted as the *capacity* reference method, not as a replacement for the selectivity ratio.

## Backtest pre-registration discipline (added 2026-09-24 — deep loop)
- **Kill condition required.** Every hypothesis pre-registration carries a kill condition up front, not just a success bar. A hypothesis without one survives on vibes — the market-structure lead lasted two cycles on thin evidence because only v3's bench rule had a kill clause. Three-zone reads (clear / inconclusive / fail) with asymmetric read rules stay the format.
- **Evaluability gate (standing rule, 2026-10-06 — from the x_lesion build).** Every pre-registered threshold ships with a synthetic-data proof that each clause can both trip and clear. A bar that cannot trip is decoration: the first lesion-script draft marked cross-family correlation "insufficient" by construction, which silently neutered the pre-registered >0.7 clause — the REDUNDANT flag could never fire. Caught by a test that tried to trip the flag, fixed before the first real run. The rule binds every metric constraint any worker drafts (backtest bars, K-metric triggers, lesion flags, calibration tiers): no threshold is registered until a synthetic test demonstrates each of its clauses evaluating true at least once. Enforcement is mechanical against accident and drift — not against deliberate forgery (the marker is a string; nothing short of separate credentials or signing would stop that, and we don't pretend otherwise): `bin/register_bar.py` is the only registration path — it runs the trip/clear proof and verifies the judgment-log entry (bar_id match, confidence present, mandatory wrong_if), refusing with exit 2 anything missing either; `bin/test_register_bar.py` proves the refusal fires (no log entry, no wrong_if, failing proof, double registration all refused; complete bar accepted). A gate that has never been seen to refuse something is unverified. Workers drafting pre-registrations run this check; reviewers (K3N1) reject bars that can't show the trip.
- **Predecessor-kill consistency (standing rule, 2026-09-24, Gabe's review).** A queued hypothesis's activation condition is checked against its predecessor's kill — "activates after X resolves" is not a terminal state and is rejected. Every queued successor carries the transition table; a sentence enumerating states can be half-updated when a state is added later, a table has an obvious empty cell:

  | Predecessor terminal state | Successor action |
  |---|---|
  | CLEAR | activate |
  | PARTIAL | activate, scoped by the predecessor's PARTIAL read (redesign, not a blank check) |
  | FAIL | cancel — the kill propagates, the successor never runs |
  | INCONCLUSIVE | hold — no verdict, no activation, no change to the predecessor's verdict |

  The table is per-predecessor: a successor naming more than one predecessor carries one table per predecessor, and activates only when ALL listed predecessors sit in activating states. Chains longer than one hop resolve hop-by-hop — "predecessor" always means the immediately prior queued item, never a transitive ancestor. Queue field format (lint-checkable, single source of truth = `backtest/NEXT.md`): `- Activation: id=<qid>; predecessor=<id>[,<id>]*|none; CLEAR=<action>; PARTIAL=<action>; FAIL=<action>; INCONCLUSIVE=<action>` and `- On-predecessor-fail: <action>` (mandatory, non-empty; `n/a (no predecessor)` only when predecessor=none — the validator enforces the consistency, plus id uniqueness and that every named predecessor resolves to a real queue id: no dangling edges, no self-reference). The `on_predecessor_fail` field is schema, not an engine: requiring it at queue-time costs nothing; only walking the descendant graph and executing it waits on a machine-readable queue. Retrofit audit (run once 2026-09-24 against every open queue item): cycle 4 has no predecessor (n/a); cycle 5's sole predecessor is cycle 4 — was the vague "activates after cycle 4 resolves," now explicit CLEAR/PARTIAL with FAIL=cancel and a compensation action (fixed); inconsistency track is independent of cycle-4 outcome (n/a); Q-unblock names no predecessor (n/a). One predecessor edge existed in the queue; it is now explicit. New entries are gated by the queue validator going forward.
- **Two-stage bars for unknown-n programs (standing rule, 2026-09-24 ~22:34 CDT, Gabe's review).** Any kill condition on an aggregate dollar P&L routes through two-stage pre-registration by default: stage 1 (scan) reports n and pilot per-trade SD with the mean suppressed until bars lock; the interlock sets CLEAR/FAIL in SE units from the pre-registered z-rule (default ±1.5·SE), writes the implied dollar bars to the run log, and only then is the verdict read. Fixed dollar bars on unknown n are uninformative — the inconsistency doc's retired +$2.00/−$1.00 sat at ~+8σ/−4σ at the n=20 floor: ~4σ-safe against false-kill but ~8σ-blind to a real small edge. This generalizes cycle 3's move (bar chosen from measured power, not picked first and hoped for) into the template so it doesn't get rediscovered per-experiment. Enforcement note (2026-09-24 ~22:35 CDT): the mean-suppression is a **schema assertion**, not pipeline prose — stage-1's output schema has no `mean_pnl` field, so a script that tries to emit it fails loudly rather than succeeding quietly. Build checklist lives in the program's design doc (§9 of INCONSISTENCY_DESIGN.md); every future two-stage program gets its own. Retrofit audit (standing checklist, 2026-09-24 ~23:15 CDT, Gabe's review): any hypothesis pre-registered before this rule gets audited against it before activation — not just the ones someone happens to remember to check, otherwise this becomes a recurring manual catch instead of a closed gap. First application: cycle 4 (pre-registered 22:24, before the rule) — audit clears it as-is (primary is a cap-ratio count statistic; guardrail is Brier edge, not dollar P&L; the two-stage dollar-P&L rule is not triggered). Cycle 5 (rally-b, first specced ~15:50 under the old fixed-bar pattern) — audit fails it (fixed ±1¢ bars on unknown n); retrofitted to the two-stage discipline in the cycle-5 entry above.
- **Cycle 4 (locked, next run): selectivity test.** Vol-touch-v2 (EWMA 24h vol, martingale drift), EV floor 2¢ → 10¢, six cached short-horizon one-touch markets, all else identical. PRIMARY decision variable: cap ratio < 10x on ≥4/6 runs (count statistic). GUARDRAIL: aggregate Brier edge ≥ −1¢. Read: CLEAR (ratio clears AND edge > +1¢) → tighten F's origination EV floor to 10¢; PARTIAL (ratio clears, edge in [−1¢,+1¢]) → selective but edge unproven, next step is bigger-n or the discrete-monitoring continuity correction; FAIL (ratio ≥ 10x on ≥3/6, or edge < −1¢) → bench the vol-touch program entirely, F pivots to news/event-driven origination research. Kill condition executes as written — no fifth price-action cycle. Full spec: `backtest/NOTES.md` 2026-09-24 ~22:24 entry.
- **Diagnostic addendum (2026-09-24 ~22:29 CDT, Gabe's review — AaU arrived after this cycle was locked):** AaU's thesis finds closed-form one-touch barrier pricing explains >95% of price variance with no Granger causality to BTC — the vol *input* was always the only variable that mattered, not the drift model v3 tested. This does not disturb the locked bars: cycle 4 tests *selectivity* (is the cap doing the loss-limiting?), AaU is about *pricing correctness* — orthogonal axes, and mutually consistent (if pricing is solved given vol, losses come from indiscriminate entry, which is exactly what the floor tests). Report the pure closed-form barrier pricer (AaU) edge on the same six splits as a NON-DECISION diagnostic comparison — no bar attached, lock intact.
- **Cycle 5 (candidate, activates ONLY on cycle-4 CLEAR or PARTIAL):** rally-b replication on 2–3 NEW weekly one-touch windows (fresh zero-spend gamma fetch). If cycle 4 FAILS, the vol-touch program is benched entirely and cycle 5 does not run — a replication would be a fifth price-action cycle, contradicting cycle 4's kill. Retrofitted to the two-stage discipline 2026-09-24 ~23:15 CDT (see retrofit audit below): n floor ≥20 pooled trades (pre-declare enough windows to expect n≥20 at ~10 trades/window; if realized n<20 the test is recorded underpowered/not-run, not read); stage 1 reports n and pilot per-trade SD with the mean suppressed, interlock sets CLEAR/FAIL at ±1.5·SE (default z-rule). Read: CLEAR (edge > +1.5·SE AND cap ratio < 10x) → venue signal confirmed, investigate the venue mechanism; INCONCLUSIVE → no verdict, no change to the cycle-4 verdict, no further price-action cycles; FAIL (edge < −1.5·SE) → rally-b was luck, close the book on vol-touch permanently. Do not run before cycle 4 resolves — one variable at a time. Power note: at cycle 3's measured per-trade SD (12.3¢), n=20 → ±1.5σ ≈ ±4.1¢; a true +2¢ edge reads inconclusive more often than not — the honest price of small n, and why inconclusive → no-change is the safe read.
- **Killed 2026-09-24:** the market-structure hypothesis (thin long-horizon ladders vs weekly one-touches). a/b pattern flips sign by regime (rally: one-touches +5.3¢ vs ladders −5.3¢; chop: ladders +3.3¢ vs one-touches −8.4¢); microstructure literature independently says longtail markets carry ~196% median spreads — informationally opaque, not exploitable. Record stands in `backtest/runs/CYCLE3_SUMMARY.md`.
- **New track (incubation deliverable):** cross-contract inconsistency episodes — Vallarino 2026 found 1,035 episodes across 52 related Polymarket pairs, 8h median correction, 72% within a day. First edge candidate from market *structure* rather than price action. Design doc: `backtest/INCONSISTENCY_DESIGN.md` (to be written). Paper-universe check: S/F may range .com as R&D; M only if .us-discoverable.

## Self-improvement loop
- After each trading session: review data feed gaps, missed signals, execution errors, strategy performance.
- Record edge cases, better heuristics, code fixes, and dead ends in LESSONS.md so nothing is retried blind.
- When a better approach is found (script, monitoring check, signal filter), rewrite that part of the process and note why.
- Spec updates here are mandatory, not optional.

## Architecture rulings — closed-loop proposals (Gabe, 2026-09-26 ~03:01 CDT)
- **Forced exploration deployment: VETOED, struck completely.** Forcing capital into zero-history markets is fixed-stake theater and manufactured action. Capital moves only through the gates (5pt EV band, Price Block). Not queued, not parked — struck.
- **Blind/entity-redacted forcing: SANDBOXED.** Never wired into the live loop. Handed to R as an offline calibration gym: Nightwatch may evaluate redacted order books to test pattern recognition and generate proposals; it cannot force a trade. (Queued for R's charter.)
- **Automatic news-triggered exits: VETOED as automation.** An LLM parsing a news feed may not execute capital. News may generate a kill PROPOSAL in `proposals/pending/`; the operator (K3N1) signs every exit. The pen stays on the operator's side of the desk — this is the hand-propagation rule applied to exits.
- **Shadow-run prompt amendments: APPROVED, wired 2026-09-26.** Behavioral version control via `bin/amend_prompt.py`: every prompt/prose amendment goes snapshot → apply → validate (py_compile + run_tests.sh + step-0 audits + JSON parse of touched .json); any red reverts idempotently to the pre-apply snapshot, and `LAST_GREEN` (in `hidden_files/prompt_versions/`) advances only on green. Scope is goal-root prose/tooling only — `hidden_files/` state and outside-root paths are refused (exit 3). `rollback` restores the green state of `LAST_GREEN`. Usage: `bin/amend_prompt.py apply --file REL=CONTENT_PATH --intent TEXT --author TEXT`.

## PAPER.md projection architecture (Gabe's rulings, 2026-09-26)
- **The JSON ledger (`hidden_files/book_ledger.jsonl`) is the singular source of truth.** PAPER.md's `## Ledger` table is a deterministic projection built by `build_paper_view.py` — never hand-edited, never written by `book_trade.py` (the booking script never mutates Markdown by construction).
- **Projection contract:** every `book` row carries `thesis` (one line) and `ev_gate` (`originated`|`near-gate`; X derives `sandbox`, directives derive `directive`). The projector FAILS LOUDLY (exit 2, names receipts) on missing fields. Repair via `book_trade.py set-display` (metadata patches only — never status/prices/P&L), never by editing PAPER.md.
- **Probability semantics (2026-09-27 repair):** PAPER's `p` column shows `win_p` = P(booked side wins), stored canonically on the ledger row at booking time and rendered verbatim — never derived from `p_yes` (which is provenance only). The 2026-09-26 migration caught and fixed a backfill that stored `p_side` as `p_yes` on a No row (`bk-backfill-09`: 0.88 → 0.12); the 2026-09-27 repair backfilled `win_p` on all 18 legacy rows with per-row provenance (`win_p_star`, `win_p_provenance`), preserving the original 0.88 in `p_yes_original`.
- **Worker order:** the hourly worker runs `build_paper_view.py` LAST, after all booking/exits/settlements/audits/state maintenance. Byte-stability verified by double-run.
- **Driver-concentration gate (CODE, 2026-09-26):** max 2 open M/S/F/Q/C positions per macro driver (absolute — directives count, X exempt as mirror). Grandfathered existing exposure; no new Iran/Hormuz until below 2.

## Token P&L — the incentive deal (Gabe, 2026-09-26 ~22:05 CDT)
- **The deal:** K3N1 may spend tokens freely, but the spend is bought with coin actually earned. Every Nightwatch cycle tabs its token cost in `hidden_files/token_ledger.jsonl` (`bin/token_ledger.py`; append-only, v0 conservative estimates by cycle type, calibrated against billing later). Tab starts at zero 2026-09-26 — sunk build-phase cost is not billed.
- **The milestone:** $10 → $100 in *realized* Polymarket USD (paper P&L never counts). At $100: $50 buys token allocation, $50 becomes the new trading stake. Thereafter realized profits split 50/50 between token allocation and stake growth, tab kept current. The split is the default, not a lockbox — Gabe can withdraw anytime.
- **Operations:** LIGHT-by-default effective immediately (resolves the pending token-mode choice); FULL only on real signals. The 90s hook stays as-is (cheap, always on).
- **The firewall (why this doesn't manufacture trades):** gates, quarter-Kelly sizing, R red-team, and never-manufacture-action are CODE/doctrine — unchanged. The incentive *prices the patience the gates already require*: a quiet LIGHT cycle watching is cheap; a FULL cycle hunting edge that isn't there deepens the tab. Manufacturing trades has negative expected token-P&L. Only realized USD repays the tab.
- **Circuit breaker:** monthly tab review in the daily standup. A growing tab with zero realized profit is a structural flag for Gabe's review — not an auto-shutdown (24/7 action stands).
- **The apex-predator inequality (Gabe, 2026-09-26 ~22:10 CDT):** a system acts only when `EV > (Compute Cost + Market Friction)`. Compute cost is now measured per cycle (token_ledger.py); market friction is spread/slippage. Burning capital to look busy is parasitism; dormancy until the inequality clears is the equilibrium strategy. Status: installed as principle — per-candidate compute-cost attribution is unbuilt, so it is not yet a coded gate.
- **Honest math (recorded, not sanded):** under the gates ($1/trade start, 5–15pt edges, quarter-Kelly), $90 of profit ≈ 600–1,000 winning trades ≈ months, and only if real edge exists. One graded paper datum so far (a loss). The milestone is a mountain; the first job is still proving edge exists.

## Phase 3.1 optimizer scaffold (2026-09-26, strictly off-path)
- `optimizer.py`: pure stateless function `optimize_portfolio(snapshots, portfolio, ...)`. Kalman update fuses noisy edge observations with prior `(P_0, c_hat_0)`; volatility-scaled Huber cap robustifies outliers; Kelly-style sizing (`edge/variance`); L1 portfolio constraint scales down proportionally when gross exceeds the limit. Zero-volatility markets get zero position (never divide by zero, never guess).
- **Unwired by design:** no imports from any production module, no ledger reads, no booking calls, no hook/auth/shadow-soak wiring. Synthetic tests only (`test_optimizer.py`: 17/17 suite green). Promotion to any live path requires Gabe's explicit approval + a new ruling.

## Cadence
- **Price reflex** (`nightwatch-price-watch` hook, ~90s, silent unless wake alert): every market in desks/WATCHLIST.json; wakes the manager on band entry (78–97¢ / 3–22¢), big moves, or paper-position danger (~5¢ warn / ~10¢ mechanical exit).
- **Hook repair 2026-09-26 (the first true integration test caught two live defects):** (1) the D-004 trap block was appended *after* the terminal `silent`/`wake` branch — both `exit 0`, so the 90s hook never evaluated traps; it now runs *before* the single terminal emission (a crossing can land on a tick with no price events). (2) `book_out=$(...)` under `set -e` would have killed the loop subshell on REJECT=3/kill=4 *before* `settle` ran, orphaning the `triggered` event — now `brc=0; ... || brc=$?`. The same first run proved the *wake* path had never worked in production: `log "price events"` passed the events *array* to the runtime's object-only validator (`jq -ce 'select(type=="object")'` exits 4), so every event-bearing tick died before `wake` — 87 failed invocations, zero wakes in the log. Fixed by wrapping: `log "price events" "{\"events\":$payload}"`. Regression guard: `test_hook_traps.py` (accept/reject/kill/dry-run/ordinary-wake, sandboxed, stubbed curl, no network). Lesson: dead code rots invisibly — the trap block and the wake path were both broken since introduction because no end-to-end run ever exercised them; dry runs don't count. (Gabe's ruling 2026-09-26: the binary floating-point boundary quirk in the move detector stays as-is — a genuine breakout persists across 90s ticks and gets caught on the next one; a move that only ever touches the exact step boundary wasn't a breakout.)
- **Hourly brain** (cron `polymarket-market-watch`, ~:48): news/catalyst sweep (Google News RSS primary since 2026-09-24; web search depth-only when its credential recovers; browser last resort), calibration, full desk-manager loop, WATCHLIST maintenance, STATUS.md heartbeat, dashboard snapshot.
- **Daily deep loop** (07:11 CDT, cron `polymarket-trading-loop`): study → decide → reflect (1-2-3); updates STRATEGY/QUEUE/LESSONS/NEWS/PAPER and the daily log. Quiet completion = no user-facing message by design (like the health check).
- **Fire-time ping** (07:13 CDT, cron `polymarket-trading-loop-fire-ping`): owns the trading loop's fire announcement — verifies dispatch via cron.runs and posts `polymarket-trading-loop fired @ <scheduled_for_local>`; also patches the loop's entry in cron_snapshot.json so the dashboard can't show stale "not fired". Reports a missed dispatch as structural.
- **Daily standup** (~6 PM CDT, cron `polymarket-daily-standup`): what happened (trades, P&L, uptime/errors); what changed about the process and why; what's next; decisions needed.
- **Health check** (every 6h, cron `polymarket-health-check`, silent unless broken): data feed reachability, open-position sanity, stop-condition watch.
- **Task queue** (QUEUE.md): running backlog, worked in priority order. Mission-serving work only — no invented busywork.

## Client
`polymarket_us.py` in this workspace. Wiring verified 2026-09-24 against docs.polymarket.us and the official Python SDK (byte-identical auth headers). Public gateway needs no auth; authenticated calls need Gabe's one-time pasted secret.

2026-09-24 unlock: the .us markets-list API was serving stale data (Oct–Dec 2025 only), making the gated real-money universe look like three retired slugs. A browser inventory scan the same day mapped the real venue (QCX LLC, CFTC DCM — NFL/CFB/MLB/Boxing/Politics/Crypto/Weather/Tech/Culture/Economics). The tradeable universe is now discoverable; the bottleneck is edge discovery, not access.
