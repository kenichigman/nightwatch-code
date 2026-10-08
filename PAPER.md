# PAPER.md — paper trading books (24/7 experience machine)

Gabe's directive 2026-09-24: paper books run in the background, always. Free data, free reps, scored relentlessly. No key needed — fully autonomous.

## Books (Gabe's org design 2026-09-24: seven runners — the foundry's first litter Q/C/R added ~08:12 CDT)

### Book M — "Mirror" — LOW risk taker (proves the recipe under identical constraints)
- Start: **$10.00** paper | Size: **$1/trade**
- Gates: identical to STRATEGY.md (80–95¢ band, EV positive across p ± 5 pts, resolution clarity, 1–4 week catalysts, no 99¢ scalps)
- Operated directly by the floor manager (no isolating the two Ms — one mind, one judgment)
- Purpose: would the real account have made money if every gated candidate had been taken? A flat M is M working.

### Book S — "Scaled" — MEDIUM risk taker (sensible aggression at professional size)
- Start: **$500.00** paper | Size: **$10/trade** (2% — professional sizing the $10 account can't afford)
- Mandate: take every M-booked trade at $10 (the overlap = pure sizing-effect measurement) PLUS selective near-gate opportunities M must pass on (75–80¢ / 95–97¢ edges, wider-catalyst theses) — each with explicit EV math (EV > 0 central, positive across p ± 5), checkable resolution, and a logged reason M's gates excluded it. Max 2 risk slots per theme.
- Purpose: what does a funded, sensibly aggressive book look like? The $10→$500 question, answered in simulation.

### Book F — "Frontier" — HIGH risk taker (K3N1's origination book — the Nightwatch dataset)
- Start: **$10.00** paper | Size: **$1/trade**
- Mandate: originated theses — sentiment fades ("bet against people"), research-validation, experimental edges. This is where K3N1 runs its own ideas.
- Entry bar (paper-appropriate, still honest): (a) explicit probability estimate p with a dated thesis, (b) EV = p − price > 0 at the central estimate, (c) publicly checkable resolution. The 80–95¢ band and the ±5pt fortress are real-money guards — Frontier logs the p-range but doesn't require it to clear, because measuring calibration IS the dataset. No booking without a genuine p > price belief. Never manufactured.
- Personality shapes WHAT F looks at, never whether the EV has to be real.
- Caps: max 8 open positions, max 5 new trades/day (raised from 3 by Gabe 2026-09-24 ~08:08 CDT — hunt wider, same gates).
- Created 2026-09-24 ~02:15 CDT on Gabe's order: "always have 3 theoretical books going... the origination of those paper books will be all you."

### Book X — "Empire" — the exploration account
- Start: **$1,000,000** paper | Size: flat **$20,000/trade** (2%)
- Mandate: EXPLORE. Originates freely across markets, thesis families, and horizons — including everything the gated desks reject — to produce quantified understanding of the market. We are an information firm: X's product is priced information, not P&L.
- No EV gate binds X (the gate is the assumed-risk model under test). Honesty gates bind: thesis schema, driver taxonomy, ledger integrity. Every exploration pre-registers its quantitative question and kill condition.
- **Unscored sandbox:** excluded from the calibration log, Brier scoring, oversize-flag math, and any real-money inference. Quarantined ledger below, labeled sandbox. Exploration doesn't get to vote on the math.
- **Liquidity honesty:** at $20k/trade most books can't fill. X checks visible depth at entry; if depth < stake, logs `capacity-constrained` and books a partial fill at available depth — the unfilled remainder is the data (this edge doesn't survive size).
- Graduation: a thesis family that demonstrates edge in X graduates upward through the normal gates — that is how exploration earns real capital.
- Rechartered 2026-10-05 to Gabe's stated original intention ("an account where we have a lot of money and we find what works" — "explore market without assumed risk" — "we are an information firm seeking quant understanding of market"). Prior shadow-amplify mandate retired; legacy shadows stand.

### Book Q — "Quant" — MEDIUM risk taker (the sports-model rat)
- Start: **$10.00** paper | Size: **$1/trade**
- Mandate: originate quant edges in the .us sports inventory (NFL/CFB/MLB/Boxing) — model-implied p vs market price, .us-discoverable so winners graduate to M.
- Differentiation: domain (sports-quant) + source (data). First rat in virgin territory (mapped 2026-09-24, never hunted).
- Created 2026-09-24 ~08:12 CDT — foundry first litter (Gabe: "lots of iterative rats running out testing any # of paths").

### Book C — "Contrarian" — HIGH risk taker (the fade rat)
- Start: **$10.00** paper | Size: **$1/trade**
- Mandate: originate sentiment fades cross-domain — documented sentiment extreme + dated thesis for why the crowd is wrong. Fading is not hating: "people are excited" is not a thesis.
- Differentiation: thesis type (fades) + source (sentiment).
- Created 2026-09-24 ~08:12 CDT — foundry first litter.

### Desk R — "Red-team" — META (no book)
- No bankroll. R reviews every originated thesis (F/Q/C, S near-gate adds) and writes kill-notes (HARD/SOFT/MISS) — advisory, never a veto. Scored on kill precision in its own ledger (desks/R.md), not P&L.
- Created 2026-09-24 ~08:12 CDT — foundry first litter. The maze simulating itself.

## Fill realism (anti-self-deception rules)
- Paper fills record at the **adverse touch**: buying → ask, selling → bid. Never the mid.
- **0.5¢ adverse slippage haircut each way** (audit resolution 2026-09-24 ~08:50 CDT): buys fill at ask + 0.5¢, exits at bid − 0.5¢, at $1–$10 sizes. Book entries are LOGGED at the haircut-adjusted price; the raw touch is noted in the trade line. This is a standing honesty tax, not a liquidity model.
- If book depth is unavailable, use last price + haircut and tag the entry `assumed-fill`.
- $1–$10 sizes are negligible vs Polymarket liquidity on tracked markets — note it explicitly if a market is thin.
- Every entry timestamped (CDT). Hourly runs keep timestamps fresh.

## Position rules
- Max **8 open positions** per book (per-desk cap; shared guardrail SPEC.md #9); max **3 new paper trades** per book per day (F: 5/day — raised by Gabe 2026-09-24 ~08:08 CDT).
- Correlated markets (e.g., Fed-hike month contracts) count as **one** risk slot across both books.
- Default: hold to resolution.
- Exit early only if: (a) thesis invalidated by dated news, or (b) repriced fair value moved **10¢+** against entry (discipline cut).

## Ledger

<!-- LEDGER-TABLE-BEGIN -->
| Date (CDT) | Book | Market | Side | Entry ¢ | p | Size $ | Thesis (1 line) | EV gate | Exit ¢ / resolved | P&L $ | Fill | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-24 02:07 | F | ipcc-openai-2026-09-30 | No | 99 | — | 0.99 | Altman ruled out 2026 IPO on record (Fortune 9/12); WSJ 9/15: IPO expected 2027 | directive | 85 (assumed-fill, 08:47 CDT) | −0.14 | v1 | mechanical exit at −14¢ adverse (≥10¢ rule); Yes repriced 1¢→15¢ on thin ask-only .us book (bid null), no supporting news; thesis not news-invalidated — pure price-rule exit, no opinion override |
| 2026-09-24 03:24 | F | sept-btc-reach-87500 (.com) | Yes | 39 | 0.60* | 1.00 | One-touch $87.5k by 9/30 23:59 ET; month high $87,386 vs $84,179 spot — needs +3.95% in ~6.8d; reflection-principle model P(touch) ~55–65% at 2.5–3.5% daily vol; Yes ask 39¢ deep ($7.3k) | originated | 26 (bid touch, 04:50 CDT) | −0.33 | v1 | mechanical exit at −13¢ adverse (≥10¢ rule); spot fell away from barrier; correlated 90k leg (−5.1¢) and dip-80k leg (+8.55¢) held — strangle ladder intact |
| 2026-09-24 03:37 | S | btc-reach-85k-from-sep23 (.com) | Yes | 76 | 0.85* | 10.00 | One-touch $85k from 9/23 by 9/30 23:59 ET; spot $83,893 needs +1.3%; measured vol 2.37% (30d) / 3.39% (7d) → model P(touch) 83–88%, central ~85%; EV +9¢, fortress holds (80>76); M's band excludes it (76<80) | near-gate | 62 (bid touch, 04:50 CDT) | −1.84 | v1 | mechanical exit at −14¢ adverse (≥10¢ rule); BTC spot ~$83.1k; thesis not invalidated by news — pure price-rule exit, no opinion override |
| 2026-09-24 03:37 | F | btc-dip-80k-from-sep18 (.com) | Yes | 35.8 | 0.50* | 1.00 | One-touch DOWN to $80k from 9/18 by 9/30; spot $83,893 needs −4.6%; measured vol → model P(touch) 44–59%, central ~50%; EV +14.2¢; completes BTC-Sep vol strangle w/ 87.5k+90k longs | originated | 23.45 (bid touch, 12:00 CDT) | −0.12 | v1 | mechanical exit at −11.85¢ adverse (≥10¢ rule); R HARD kill (10:48) confirmed — vol-crush/pin into Fri $16B expiry priced in; thesis not news-invalidated, pure price-rule exit |
| 2026-09-24 09:52 | X | sept-btc-reach-90000 (.com) | Yes | 17.1 | — | 7124.53 | SHADOW: F-originated one-touch $90k thesis (F entry 17.5¢, model central ~39%, EV +21.5¢); X entry at prevailing ask 16.6¢ + 0.5¢ haircut | sandbox | 6.8 (19:48 CDT) | −4291.54 | v1 | attempted $20,000; capacity proxy (5% of 24h $vol $142,490) → filled $7,124.53 (~41,661 sh); $12,875.47 capacity-constrained; unscored; closed alongside F mechanical exit @6.8¢ (adverse 10.0¢); first X shadow fill (Gabe: "see X make paper trades") |
| 2026-09-24 10:52 | X | bitcoin-above-80k-on-september-25-2026 (.com) | No | 2.6 | — | 3405.41 | SHADOW: C-originated daily-barrier fade (C entry No 5.3¢, p=0.12); X entry at prevailing No ask + 0.5¢ haircut | sandbox | settled YES 11:00 CDT | −3405.41 | v1 | shadow graded: No@2.6¢ filled $3,405.41; unscored sandbox |
| 2026-09-24 10:52 | X | another-fed-rate-hike-in-2026 (.com) | No | 9.5 | — | 1146.03 | SHADOW: C-originated hawkish-certainty fade (C entry No 9.5¢, p=0.25); X entry at prevailing No ask + 0.5¢ haircut | sandbox | open | — | v1 | attempted $20,000; capacity proxy → filled $1,146.03; remainder capacity-constrained; unscored |
| 2026-09-24 12:55 | X | us-x-iran-ceasefire-continues-through-september-30-20260917 (.com) | No | 13.5 | — | 10954.58 | SHADOW: F-originated escalation fade (F entry 13c, p=0.18, EV +5c); X entry at prevailing No ask 13.0c + 0.5c haircut | sandbox | 2.8 (01:32 CDT) | −8682.52 | v1 | attempted $20,000; capacity proxy (5% of 24h $vol $219,091.53) -> filled $10,954.58 (~81,149 sh); $9,045.42 capacity-constrained; unscored |
| 2026-09-24 19:48 | X | strait-of-hormuz-traffic-returns-to-normal-by-december-31 (.com) | No | 79.5 | 0.88* | 10082.36 | SHADOW: F-originated hormuz fade (F entry 79.5c, p=0.88, EV +8.5c); X entry at prevailing No ask 79.0c + 0.5c haircut | sandbox | open | — | v1 | attempted $20,000; capacity proxy (5% of 24h $vol $201,647.24) -> filled $10,082.36; $9,917.64 capacity-constrained; unscored |
| 2026-09-24 22:15 | C | bitcoin-above-80k-on-september-25-2026 (.com) | No | 5.3 | 0.12 | 1.00 | 95.45¢ certainty w/ spot $83.3k sliding into $16B Friday expiry; ~4% drop in ~24h plausible; EV=+6.7¢ at honest No-ask touch (4.8¢ + 0.5¢ haircut) | originated | settled YES 21:45 CDT | −1.00 | v1 | first graded datum: No@5.3¢ (p=0.12) vs YES outcome; Brier (0.12−0)²=0.0144; C book −$1.00 |
| 2026-09-24 22:15 | C | another-fed-rate-hike-in-2026 (.com) | No | 9.5 | 0.25 | 1.00 | 91.5% crowd certainty on a 15-mo macro call is the extreme; Barr/Williams words≠votes; EV=+15.5¢ at honest No-ask touch (9.0¢ + 0.5¢ haircut) | originated | open | — | v1 | C's first originations; fade of recency-biased hawkish certainty |
| 2026-09-24 22:15 | F | ipcc-anthropic-2026-09-30 | No | 99 | — | 0.99 | WSJ 9/19: IPO shifted to November; S-1 still confidential, exchange unpicked | directive | settled NO 01:27 CDT | 0.01 | v1 | assumed-fill; Gabe's direct order 2026-09-24; research-validation |
| 2026-09-24 22:15 | F | cpc-btc-150k-09-30-2026 | No | 99 | — | 0.99 | BTC ~$84k needs +79% in 7 days; WSJ: analysts skeptical prior highs repeat | directive | open | — | v1 | assumed-fill; Gabe's direct order 2026-09-24; research-validation |
| 2026-09-24 22:15 | F | sept-btc-reach-90000 (.com) | Yes | 17.5 | 0.39* | 1.00 | One-touch $90k by 9/30; needs +6.9% from spot in ~6.8d; model P(touch) ~30–44%, central ~39%; Yes ask 17.5¢ | originated | 6.8 (19:59 CDT) | −0.61 | v1 | quant one-touch model; correlated w/ 87.5k = one risk slot |
| 2026-09-24 22:15 | F | strait-of-hormuz-traffic-returns-to-normal-by-december-31 (.com) | No | 79.5 | 0.88 | 1.00 | Escalation (Houthi strikes, Saudi intercepts, 80-nation condemnation) kills near-term Hormuz normalization; resolves 2027-01-01, checkable | originated | open | — | v1 | No ask 79.0 (gamma Yes bid 0.21) + 0.5 haircut; EV=+8.5c central (+3.5c under -5pt); r=0.96; 5th F origination of 2026-09-24, daily slots full |
| 2026-09-24 22:15 | F | us-x-iran-ceasefire-continues-through-september-30-20260917 (.com) | No | 13 | 0.18 | 1.00 | Iran escalation cluster (CBS fresh-threats, Netanyahu UN tease, 80-nation Hormuz demand, oil $107) vs stale 87.5¢ Yes price; ceasefire breaks by Sep 30, news-checkable | originated | 2.8 (01:32 CDT) | −0.78 | v1 | assumed-fill (gamma mid 12.5, No ask 13.0 + 0.5 haircut); EV=+5c at central (0.18-0.13); 4th F origination of 2026-09-24, 1 slot remains; adverse 7.5c as of 2026-09-26 14:43 hook (past 5c warn, HOLD per rule — S's sister leg mechanically exited same poll) |
| 2026-09-24 22:15 | S | us-x-iran-ceasefire-continues-through-september-30-20260917 (.com) | No | 15.5 | 0.22 | 10.00 | Escalation cluster tonight (UN Hormuz demand, Saudi intercepts, Houthi Riyadh/Aramco claims) vs stale 85.5c Yes; ceasefire breaks by Sep 30 | near-gate | 5 (No bid touch, 14:43 CDT) | −6.77 | v1 | mechanical exit at −10.5¢ adverse (≥10¢ rule, hook 14:41 position_exit_trigger, gamma-verify Yes 94.5); Yes repriced 84.5¢→94.5¢ over ~2d; thesis not news-invalidated — pure price-rule exit, no opinion override |

| 2026-09-26 07:24 | F | fed-oct-hike25 (.com) | Yes | 65.5 | 0.72 | 0.45 | Cross-venue Fed-pricing gap: CME FedWatch Oct +25bp 77.5% (Thu) vs Polymarket Yes ask 65c; Williams 09-24: another hike "reasonable"; p=0.72 shaved for single-comment overreaction risk + data-dependence; EV +6.5c at 65.5c all-in (ask + 0.5c haircut); resolves Oct 28 FOMC, non-standard sizes round up to nearest 25 | originated | 51 (13:15 CDT) | −0.10 | v1 | receipt bk-20260926-009; mirrored to worker_state + WATCHLIST (fed-oct-hike25) 2026-09-26 07:48 cycle; ledger row backfilled after 07:11 deep-loop timeout |
| 2026-09-26 08:56 | X | fed-oct-hike25 (.com) | Yes | 65 | — | 9855.77 | SHADOW: F-originated cross-venue Fed-pricing gap (F entry Yes 65.5¢, p=0.72, EV +6.5¢); X entry at prevailing ask 65.0¢ | sandbox | 51 (13:15 CDT) | −2122.78 | v1 | receipt bk-20260926-010 (shadow_of bk-20260926-009); attempted $20,000; capacity proxy (5% of 24h $vol $197,115.35) → filled $9,855.77; $10,144.23 capacity-constrained; unscored; PAPER.md row backfilled 2026-09-26 12:48 cycle (ledger-only since booking) |

| 2026-09-27 16:53 | F | will-china-invade-taiwan-before-2027 | No | 0.9705 | 0.97 | 0.95 | Sentiment fade: fear-premium overprices Taiwan invasion at 3.45c vs <=1% base rate; no dated escalation catalyst | originated | 0.9705 (16:54 CDT) | 0.00 | v1 | assumed-fill: CLOB book degenerate (bid 0.001/ask 0.999 stubs), entry at gamma lastTrade 96.55c +0.5c haircut; cycle 20260927-1648 |
| 2026-09-27 17:16 | F | f-btc875k | No | 0.8 | 0.95 | 0.95 | Sentiment fade: Sept BTC $87.5k touch; Yes ask 21c vs reflection-principle model p_touch ~4.7% (EWMA 1.82% 3d vol); buy No at 80c, central EV ~15c | originated | 0.8 (17:29 CDT) | 0.00 | v1 | Model: martingale GBM, EWMA lambda=0.94 hourly sigma 0.214% over 350h, 3d sigma 1.82%, log barrier 3.62%; MC 60k paths -> p_touch 3.9%. Binance high not yet touched (market live at 21c/79c proves it). Prior F touch-side position on same market closed 09-24 (mechanical exit -13c); this is the inverse fade. No ask 0.80 depth $1.1k+$30.6k at .81, 1c spread. |
| 2026-09-27 17:16 | X | f-btc875k | No | 0.8 | — | 3184.55 | SHADOW: F-originated Sept BTC $87.5k touch fade (F entry No 80c, model p_touch 4.7%, central EV ~15c); entry at prevailing No ask | sandbox | 0.8 (17:29 CDT) | 0.00 | v1 | Capacity proxy: 5% of trailing-24h volume $63,691 = $3,184.55; cap ratio 6.28x < 10x bar. No-ask depth: $1.1k @0.80 + $30.6k @0.81, 1c spread. X unsorted/quarantined; shadow-amplifies F-cleared thesis only. |

| 2026-09-30 08:15 | F | will-bitcoin-reach-87pt5k-in-september-2026 | Yes | 17.3 | 0.30 | 0.35 | F vol-touch: BTC 7.5k one-touch by 09-30, Yes@17.3c on overnight momentum | originated | 3.5 (08:44 CDT) | −0.28 | v1 | Hook 2026-09-30 08:13 CDT big_move +5.75c (11.3c->17.05c mid, 17.3c ask). Spot ~85425; needs 87.5k wick (+2.43%) by 23:59 ET (~14.8h). 24h range 3.24%, +2.2% on day. Reflection est ~0.375, haircut to 0.30 for day-high mean-reversion. Short-horizon one-touch = F's allowed vol category (post 0-for-3 bench). Dated: expires tonight. |

| 2026-10-01 19:57 | S | will-there-be-no-change-in-fed-interest-rates-after-the-october-2026-meeting-20260617190324031 | Yes | 74 | 0.80 | 10.00 | join washed-out October hike bets: dovish tape (Reuters/WSJ 10-01) vs Williams late-2026 chatter; p=0.80 vs 74-75c ask | near-gate | open | — | v1 |  |
| 2026-10-01 19:57 | X | will-there-be-no-change-in-fed-interest-rates-after-the-october-2026-meeting-20260617190324031 | Yes | 75 | — | 20000.00 | shadow of S near-gate no-change-October (dovish tape); p=0.80 vs 75c ask | sandbox | open | — | v1 |  |

| 2026-10-05 15:35 | X | nfl-atl-no-2026-10-06 | Yes | 48 | 0.54 | 20000.00 | NFL home teams win ~57%; Falcons at home priced 47.5% — base rate says buy | sandbox | settled YES 07:14 CDT | 21666.67 | v1 |  |
| 2026-10-05 15:35 | X | unl-fra-bel-2026-10-05-fra | No | 7 | 0.12 | 20000.00 | 93% for a favorite in a rivalry match is extreme; fair ~88%, No worth 12c vs 7c ask | sandbox | settled YES 07:14 CDT | −20000.00 | v1 |  |
| 2026-10-05 15:35 | X | will-the-fed-decrease-interest-rates-by-50-bps-after-the-october-2026-meeting-20260617190324029 | Yes | 0.2 | 0.02 | 20000.00 | unconditional 50bp-cut base rate ~2-3% of FOMC meetings; market prices 0.15-0.2% | sandbox | open | — | v1 |  |
| 2026-10-05 15:35 | X | will-the-fed-decrease-interest-rates-by-25-bps-after-the-october-2026-meeting-20260617190324030 | Yes | 0.4 | 0.03 | 20000.00 | October cut would be a dovish surprise; 3% vs 0.4c ask | sandbox | open | — | v1 |  |
| 2026-10-05 15:35 | X | will-the-us-invade-iran-before-2027 | No | 84 | 0.90 | 20000.00 | market conflates strike risk with invasion risk; invasion needs a massive escalation ladder — No worth 90c vs 84c | sandbox | open | — | v1 |  |
| 2026-10-05 16:05 | X | unl-alb-smr-2026-10-06-alb | Yes | 97.2 | 0.99 | 20000.00 | X-001 near-certainty fade: Albania v San Marino YES underpriced per protocol (resolves 2026-10-06) | sandbox | settled YES 07:14 CDT | 576.13 | v1 |  |
| 2026-10-05 16:05 | X | elon-musk-of-tweets-september-29-october-6-2026-200-219 | No | 91.4 | 0.93 | 20000.00 | X-001 long-shot fade: Musk 200-219 tweet band YES overpriced, fade via NO per protocol (ends 2026-10-06) | sandbox | settled YES 07:14 CDT | −20000.00 | v1 |  |
| 2026-10-05 16:05 | X | will-bitcoin-reach-92k-october-5-11-2026 | No | 90.5 | 0.92 | 20000.00 | X-001 long-shot fade: BTC 92k one-touch YES overpriced, fade via NO per protocol (resolves ~2026-10-12) | sandbox | open | — | v1 |  |
| 2026-10-05 16:05 | X | unl-eng-cze-2026-10-06-eng | Yes | 89.5 | 0.91 | 20000.00 | X-001 near-certainty fade: England v Czechia YES underpriced per protocol (ends 2026-10-06) | sandbox | settled YES 07:14 CDT | 2346.37 | v1 |  |
| 2026-10-05 16:05 | X | lal-bar-get-2026-10-10-bar | Yes | 93.5 | 0.94 | 20000.00 | X-001 near-certainty fade: Barcelona v Getafe YES underpriced per protocol (2026-10-10) | sandbox | open | — | v1 |  |
| 2026-10-05 17:33 | X | will-bitcoin-reach-150k-in-october-2026 | No | 99.7 | 1.00 | 20000.00 | BTC +75% in 26 days to 50k is a 0.1% tail; No at 99.7c is near-certain | sandbox | open | — | v1 |  |
| 2026-10-05 17:33 | X | will-ethereum-reach-4500-in-october-2026 | No | 99.5 | 1.00 | 20000.00 | ETH +67% in 26 days is a 0.2% tail; No at 99.5c fades the mania | sandbox | open | — | v1 |  |
| 2026-10-05 17:33 | X | will-ethereum-reach-3600-in-october-2026 | No | 96.2 | 0.97 | 20000.00 | ETH 600 needs +33% in 26 days; fair ~2.5% vs 4.1c ask | sandbox | open | — | v1 |  |
| 2026-10-05 17:33 | X | will-ethereum-reach-3500-in-october-2026 | No | 94.4 | 0.96 | 20000.00 | ETH 500 needs +30% in 26 days; fair ~4% vs 6.2c ask, No worth 96c | sandbox | open | — | v1 |  |
| 2026-10-05 18:13 | X | 2026-balance-of-power-r-senate-d-house-444 | Yes | 27.5 | 0.38 | 20000.00 | R-Senate/D-House split is the modal midterm outcome on map arithmetic + Dem House generic-ballot lead; 65.5c on D-Senate misprices the chamber. | sandbox | open | — | v1 |  |
| 2026-10-05 18:13 | X | will-jd-vance-win-the-2028-us-presidential-election | Yes | 21.2 | 0.30 | 20000.00 | Incumbent-VP succession base rate plus early GOP consolidation around Vance supports 30% vs 20.7c ask. | sandbox | open | — | v1 |  |
| 2026-10-05 18:13 | X | will-bitcoin-reach-100k-in-october-2026 | Yes | 12.5 | 0.22 | 20000.00 | BTC 84.3k with 26 days left; Strive 169M buy + Treasury dereg tailwinds + dovish Fed tape fuel the right tail; gamble-directive lottery ticket 22% vs 12c ask. | sandbox | open | — | v1 |  |
| 2026-10-05 18:14 | X | will-gavin-newsom-win-the-2028-us-presidential-election | Yes | 8.6 | 0.14 | 20000.00 | Newsom holds the Dem establishment lane if the coalition fractures; 14% genuine probability vs 8.1c ask. | sandbox | open | — | v1 |  |
| 2026-10-05 18:14 | X | will-gadi-eizenkot-be-the-next-prime-minister-of-israel | Yes | 47.7 | 0.52 | 20000.00 | Eizenkot leads the post-Netanyahu security-candidate lane on coalition math; 52% vs 47.2c ask. Driver NOTE: taxonomy has no Israel-leadership key; mapped to iran-geopolitics as closest controlled-vocab macro-story. | sandbox | open | — | v1 |  |
| 2026-10-05 22:00 | X | will-bitcoin-reach-97pt5k-in-october-2026 | Yes | 15.5 | 0.22 | 20000.00 | Yes BTC >=97.5k Oct-31: lognormal p~0.22 vs ask 15c (spot 86.5k, golden-cross + treasury-bid drift) | sandbox | open | — | v1 |  |
| 2026-10-05 22:00 | X | will-bitcoin-reach-102pt5k-in-october-2026 | Yes | 7.5 | 0.14 | 20000.00 | Yes BTC >=102.5k Oct: lognormal p~0.135 vs ask 7c, tail priced on stale seasonality prior | sandbox | open | — | v1 |  |
| 2026-10-05 22:00 | X | will-bitcoin-reach-105k-in-october-2026 | Yes | 5.4 | 0.10 | 20000.00 | Yes BTC >=105k Oct: lognormal p~0.105 vs ask 4.9c, tail-sellers demanding realized-vol premium | sandbox | open | — | v1 |  |
| 2026-10-05 22:00 | X | will-alexandria-ocasio-cortez-win-the-2028-us-presidential-election | No | 85.3 | 0.90 | 20000.00 | No AOC wins 2028 presidency: p(yes)~0.10 via Dem-primary 0.22 x general 0.45, market pricing celebrity momentum | sandbox | open | — | v1 |  |
| 2026-10-05 22:00 | X | will-the-fed-increase-interest-rates-by-25-bps-after-the-october-2026-meeting-20260617190324032 | No | 81.5 | 0.87 | 20000.00 | No Fed +25bps Oct meeting: p(no)~0.87, hike tail dead after soft jobs + pause headlines | sandbox | open | — | v1 |  |
| 2026-10-05 23:07 | X | will-josh-shapiro-win-the-2028-us-presidential-election | Yes | 3.6 | 0.04 | 20000.00 | Swing-state governor with strongest Dem general-election profile priced 33:1 in wide-open primary; top-tier-contender base rate ~25:1 | sandbox | open | — | v1 |  |
| 2026-10-05 23:07 | X | 2026-balance-of-power-d-senate-r-house-692 | Yes | 1.7 | 0.02 | 20000.00 | Combo leg is residual of D-wave tail, priced as freak accident while wave-correlation base rate ~2% | sandbox | open | — | v1 |  |

| 2026-10-07 00:54 | X | will-gavin-newsom-win-the-2028-democratic-presidential-nomination-568 | Yes | 16.8 | 0.24 | 228.83 | Donor network + national profile; early-cycle market anchors on name-salience noise; p=0.24 vs ask 16.8c, EV +7.2c/share | sandbox | open | — | v2 |  |
| 2026-10-07 00:54 | X | will-josh-shapiro-win-the-2028-democratic-presidential-nomination-977 | Yes | 6.5 | 0.10 | 4.55 | Popular PA governor, Midwestern-moderate lane real; p=0.10 vs ask 6.5c, EV +3.5c/share | sandbox | open | — | v2 |  |
| 2026-10-07 00:54 | X | will-pete-buttigieg-win-the-2028-democratic-presidential-nomination-687 | Yes | 5.1 | 0.07 | 123.76 | 2020 IA winner at 5.1c is the mispriced insurance leg of the nomination complex; p=0.07 vs ask 5.1c, EV +1.9c/share | sandbox | open | — | v2 |  |
| 2026-10-07 00:54 | X | will-bitcoin-reach-105k-in-october-2026 | Yes | 2.7 | 0.04 | 16.04 | Panic-tape reprices October upside ladder linearly; +25pct months ~1-in-25 base rate; p=0.04 vs ask 2.7c, EV +1.3c/share | sandbox | open | — | v2 |  |
| 2026-10-07 02:58 | X | will-the-fed-increase-interest-rates-by-25-bps-after-the-october-2026-meeting-20260617190324032 | No | 16 | 0.94 | 2000.00 | Fed Oct hike No at 84.5c; p(No)=0.94, fear priced on India hike + minutes noise | sandbox | open | — | v2 |  |
| 2026-10-07 18:01 | F | us-x-iran-ceasefire-continues-through-october-31-20260917 | Yes | 71 | 0.78 | 0.10 | Ceasefire held every monthly date since June incl Sep (res 0.9995); p=0.78 vs 71c live ask -> EV +7c; resolves on public news; term-structure pair with hormuz-No (near-term calm vs medium-term shipping disruption), not a doubled bet | originated | open | — | v2 |  |
<!-- LEDGER-TABLE-END -->
`*` = backfilled 2026-09-24 ~09:10 CDT from explicit thesis centrals (no desk p was logged at booking). `—` = no p by design (directive rows; excluded from Brier scoring). The `p` column is P(booked side wins), 0–1 scale — rendered verbatim from the ledger's canonical `win_p` (2026-09-27 repair; `p_yes` is provenance only, never displayed or scored). `bin/brier.py` in the market-watch skill scores from the ledger's `win_p`, not from this column.

### Gate exceptions
- 2026-09-24 ~08:08 CDT: **Book X is an unscored sandbox** (Gabe's order). Its ledger is quarantined below and labeled `sandbox`; X rows never enter the calibration log, Brier scoring, oversize-flag math, or real-money inference.
- 2026-09-24 ~08:08 CDT: **F origination cap raised 3→5/day** (Gabe: hunt wider). Effective immediately — F has 2 origination slots remaining today. S stays at 3/day; X does not originate.
- 2026-09-24: Gabe ordered the three original 99¢ No positions onto the paper books ("makes no sense to not run the experiment"). They live in Book F as `directive` research-validation trades — this keeps Book M a pure mirror of gated decisions. Real-money gates still ban 99¢ scalps; this changes nothing there. Purpose: did our deep-read process (WSJ/Economist) correctly call three real resolutions? Tagged `assumed-fill`: .us book shows no quotable No ask; last Yes trade 1¢ on all three; entry matches the cancelled real orders' 99¢ price.
- 2026-09-24 ~03:37 CDT: Gabe's three 02:07 directive trades are EXEMPT from the 3-new-trades/day origination cap — they were his direct order, not desk origination. F originated count for 2026-09-24: 3 (87.5k + 90k at 03:24, 80k-dip at 03:58) = at cap. No more F originations today.
- 2026-09-24 ~07:15 CDT (deep loop): **paper-universe rule** — the real account trades .us only, so Book M (the mirror) may only book **.us-discoverable** markets: what the real account could actually have traded. Books S and F may range across .com as simulation/R&D — their mandate is priced information, not mirror fidelity. This resolves the parked .com-universe question. Note: .us list discovery from the VM is broken (stale 2025 data); M is effectively constrained to known-working .us slugs until the inventory scan returns.

## Queued origination candidates (Frontier pipeline)
Refreshed 2026-09-24 ~07:27 CDT (deep loop, cycle 2; browser deep-read + .us inventory). First pass: none booked — honest p ≈ price on all of them. **F is at its 3-originations/day cap for 2026-09-24 — no new F origination today regardless.**
| Candidate | Price | Why not yet | Unlock |
|---|---|---|---|
| Oct FOMC +25bp hike — Yes | 68.5¢ | No dated edge; "never buy the repricing" | Only if new hawkish data softens price |
| Fed another-hike-2026 — Yes | 90.5¢ | Fortress: deep read confirms ~90% fair; convergence priced | Hawkish surprise with dot-plot shift |
| US–Iran ceasefire 2026 — Yes | 84.5¢ | p unverifiable — no genuine p either side | Verified diplomacy/breakdown signal |
| BTC above $80k Sep 25 — Yes | 94.95¢ | Needs p ≥ 99.9%; Friday $15.6B options expiry = vol event | Only if a real volatility edge appears |
| A'ja Wilson WNBA MVP — Yes | 96.1¢ | Can't verify award status; 3.9¢ gap smells like informed flow; outside 80–95¢ band | Confirm award announcement status (end Nov 15) |
| Chiefs vs Dolphins (KC) — Yes | 85.5¢ | Fortress: needs p ≥ 91%; honest p ≈ 87–88% and IS the market line; sentiment agrees with price (no fade) | Verified injury/line news moving p ≥ 91% |
| Anthropic IPO confirmed by Nov 30 — Yes (.us) | 85¢ | Fortress: needs p ≥ 90%; honest p ≈ 82–87%; "officially confirmed" criteria unverifiable | **Public S-1 filing — the unlock event** |
| Tesla Q3 deliveries >450k — Yes (.us) | 82¢ | Needs p ≥ 87%; no delivery data | Delivery-report leaks into Oct 1–2 |
| Indiana CFB — Yes (.us) | 93¢ | Needs p ≥ 98%; no model | Never — no edge path |
| MLB postseason futures | — | Bracket still firming | Revisit when bracket firms ~09-29/30 |
| Pop-culture watchlist (awards/box office/music/sports) | — | First pass built this loop: scan works, edges not found — surveillance desk | 80–95¢ mispricing in a named cultural market |

## Book lifecycle (when books close)

Positions close at market resolution (default: hold) or early exit on thesis invalidation / 10¢+ adverse repricing. The books themselves are perpetual datasets — they don't close on a timer. Final close happens per book:

- **M (Mirror):** closes when the real-money experiment ends or the strategy is replaced. Final question answered: "would the gated strategy have made money?"
- **S (Scaled):** closes when the $10→$500 question is answered with enough resolved trades, or when real capital scales up and the simulation is redundant.
- **F (Frontier):** never finally closes — permanent R&D lab.

All three are scored in **30-day epochs** (Epoch 1: Sep 24 → Oct 24, 2026): realized + mark-to-market P&L, win rate, calibration notes in the log. Epochs score; they don't reset bankrolls mid-position.

## Scoreboard

_Reconciled by the 2026-09-24 23:19 CDT deep loop against `worker_state.json` positions (source of truth) — prior rows had drifted: S's 19:48 iran No ($10 open) was missing from S's book record, F's hormuz No ($1 open) from F's book record, F realized missed the 12:00 dip80k exit, and X's ledger lacked the two 10:52 shadows. Book-record staleness is flagged for the hourly worker's synthesis step (recompute open_risk from positions each run, per the 20:48 X lesson)._

| Book | Start | Current | Realized P&L | Open risk | Trades | Wins | Win rate | Avg edge captured |
|---|---|---|---|---|---|---|---|---|
| M | $10.00 | $10.00 | $0.00 | $0 | 0 | 0 | — | — |
| S | $500.00 | $491.39 | −$8.61 | $10.00 | 3 | 0 | 0% | exit 04:50: btc85k −14¢ adverse, rule (b); exit 14:43: iran-ceasefire No −10.5¢ adverse, rule (b); open: fed-oct-nochange Yes $10 (bk-20261001-024) |
| F | $10.00 | $7.65 | −$2.35 | $1.99 | 13 | 1 | 8% | 7 mechanical exits, all rule (b): openai-no −14¢ (08:48, −$0.14), btc87.5k −13¢ (04:50, −$0.33), dip80k −12.35¢ (12:00, −$0.34 corrected 2026-10-02; was −$0.12), btc90k −10.7¢ (19:48, −$0.61), iran-ceasefire-no −10.2¢ (2026-09-29 01:30, −$0.78), fed-oct-hike25-yes −14.5¢ (2026-09-29 13:14, −$0.10), btc87.5k-yes −13.8¢ (2026-09-30 08:44, −$0.28); anthropic-no settled NO 2026-10-02 01:27 CDT (+$0.01, first F win); btc-no $150k-Sep settled NO via fallback path 2026-10-06 19:02 CDT (+$0.01; venue still MARKET_STATE_OPEN at 19:00 deadline, flip waiting_venue→fallback_due fired 19:00:52 CDT, coinbase Sep-max $87,397.00 + kraken $87,446.70 corroborate); reconciled from book_ledger.jsonl 2026-09-29 02:58 CDT (scoreboard had missed the 09-28 19:48 btc90k exit); FLAG for hourly reconciliation: ledger exit receipts sum realized −$1.75 vs scoreboard −$2.57 (gap widened $0.60→$0.82 by the dip80k correction 2026-10-02; receipts need re-derivation — may carry the same adverse×notional bug) — the btc90k −$0.61 has no matching ledger exit (bk-20260927-020 shows 0.00); pre-existing 09-29 drift, not re-litigated this hook; open: hormuz-no $1.00 (verified from ledger 19:03 CDT) |
| X | $1,000,000.00 | $1,000,000.00 | $0.00 | $31,228.39 | 8 | 0 | — | unscored sandbox; 3 open shadows: hormuz $10,082.36, fed-hike $1,146.03, fed-oct-nochange $20,000.00 (bk-20261001-025, 2026-10-01) (open-risk recomputed from book_ledger.jsonl 2026-10-04 18:56 CDT); fed-oct shadow closed 2026-09-29 13:14 with originator exit (−$2,122.78, unscored); iran shadow closed 2026-09-29 01:30 with originator exit (−$8,682.52, unscored); btc80k shadow settled YES 11:00 CDT (−$3,405.41, unscored); 90k shadow closed 2026-09-25 19:48 (−$4,291.54, unscored) |
| Q | $10.00 | $10.00 | $0.00 | $0 | 0 | 0 | — | newborn 08:12; 4+ consecutive pass-only cycles (no model) |
| C | $10.00 | $9.00 | −$1.00 | $1.00 | 2 | 0 | 0% | btc80k-daily No settled YES (11:00 CDT), −$1.00 realized; first graded datum (p=0.12, Brier 0.0144); fed-hike No open |

## Latency-cost tracker

Real-money trades missed because Gabe couldn't paste the key in time, where the paper version won. This prices our execution latency — a number, not a feeling.

| Date (CDT) | Market / side | Paper P&L $ | Why missed | Lesson |
|---|---|---|---|---|
| — | — | — | _none yet_ | — |
