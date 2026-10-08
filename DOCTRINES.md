# DOCTRINES.md — the anti-orthodoxy schema

**Registered 2026-09-26 ~02:30 CDT, Gabe's directive.** The problem this file
solves: every Nightwatch hypothesis is required to carry a kill condition
(SPEC.md), but the *doctrines themselves* — the sizing code, the gates, the
calibration tiers, the foundry governors — carried none. A diagnostic tool
that cannot be falsified is a dogma with instrumentation. This schema applies
the same discipline to the machine that the machine applies to its beliefs.

Boorstin's warning, installed as machinery: *every new coordinate system
eventually hardens into a prison for the people who inherit it.* Prevention
is not on offer. Hardening-*detection* is.

## The schema

Every doctrine is an entry in `hidden_files/doctrine_registry.json` with
exactly these fields. No field is optional.

| Field | Meaning |
|---|---|
| `id` | `D-NNN`, immutable. Never reused, even after retirement. |
| `title` | Short name. |
| `statement` | What the doctrine claims, in one paragraph. The claim being defended. |
| `enforcement_layer` | `CODE` / `STRUCTURAL` / `MECHANICAL_PROSE` / `JUDGMENT_PROSE` (same hierarchy as SPEC.md's gate register). CODE doctrines are the most dangerous: they work, so they go unquestioned, so they become invisible. |
| `registered` | Date the doctrine entered the registry. |
| `revisit_date` | Calendar date of the next mandatory review. Not "someday." A date. On review the doctrine is reaffirmed, revised, or retired — and the revisit_date advances. A doctrine may not survive its revisit_date unexamined. |
| `kill_condition` | The explicit, pre-registered, measurable condition(s) under which the doctrine is retired or suspended. Disjunctive: ANY trigger firing kills. Each trigger states its `evaluation`: `MECHANICAL` (checked by `audit_doctrines.py`) or `MANUAL` (checked by a reviewer at revisit or when evidence surfaces). A kill condition with no measurable trigger is decoration — see AGENTS.md "a validator that can't fail is decoration." |
| `kill_action` | What happens when the kill condition fires. Not "revisit" — the specific downgrade: which layer it falls to, what replaces it in the interim, who executes. |
| `liturgy_trigger` | The silence tripwire. If the doctrine reaches `revisit_date` with **zero** entries in `history` since registration (no challenge, no anomaly, no adjustment, no R kill-note), `audit_doctrines.py` files a `liturgy-<id>` proposal: *silence is not success; it is the sound of the system going deaf.* The review must then either produce a genuine adversarial examination or record, as a finding, why none was possible. "No challenges filed" is itself the finding. |
| `history` | Append-only. EVERY challenge, anomaly, adjustment, R kill-note, review, and near-miss is appended with a date. An empty history at revisit is the liturgy condition. |
| `status` | `active` | `suspended` (kill fired, interim regime in force) | `retired` (kill fired, doctrine withdrawn). |

## Rules of the registry

1. **No doctrine without a kill condition.** A proposed doctrine that cannot
   state what would prove it wrong is not registered. It stays a hypothesis.
2. **CODE-layer doctrines get the shortest revisit intervals.** The more
   invisible the enforcement, the more frequent the examination. Default:
   CODE 90d, STRUCTURAL 180d, prose layers 90d (prose is cheap to re-read).
3. **R has standing authority to attack doctrines.** See the R-mandate
   amendment below. The red team hunts rules, not just theses.
4. **The auditor (Gabe) can retire any doctrine at will**, with or without a
   fired trigger. The Faraday slot: the outsider is always in the room.
   Overrule is recorded in `history`, not hidden.
5. **`audit_doctrines.py` runs on the same cadence as `audit_freshness.py`**
   and files to `proposals/pending/` — idempotent, loud-until-acted-on
   (exit 2 on new filings), never auto-resolving. Nothing here reaffirms,
   retunes, or retires a doctrine by heuristic. The script detects; a mind
   decides.
6. **Retirement is not deletion.** Retired doctrines stay in the registry
   with `status: retired` and their full history. The graveyard is part of
   the instrument — future doctrines are checked against how past ones died.

## The consolidation procedure (D-002, 2026-09-26)

Musashi's nerve, installed as machinery. The kill-condition schema solved
Boorstin's problem (canonization: nothing becomes unfalsifiable) but not
Musashi's (proliferation: the rules multiply). Worse, it feeds it: a
pre-attached kill condition *lowers* the psychological cost of minting a new
doctrine, so "earned by a real failure" becomes the origin story of a
compliance manual — every incident mints a rule, no incident un-mints one.
The registry holds at most seven active doctrines (`max_doctrines` in the
registry JSON; D-002 counts itself). Seven is the 7±2 bound: the registry
must fit in one mind at once, because a doctrine you cannot hold alongside
the others cannot constrain behavior.

At cap, a new doctrine enters only through one of three gates, in order:

1. **Merge.** Can an existing doctrine's principle be rewritten to cover the
   new failure mode *without weakening any of its kill triggers*? If yes, the
   existing doctrine is rewritten (history appended, triggers preserved or
   strengthened) and the candidate dies as a separate entry. No new number.
   History event: `doctrine-merged`.
2. **Displacement.** Does the new principle *strictly generalize* an existing
   doctrine — cover every failure mode the old one covers, plus the new one,
   with kill triggers at least as falsifiable? If yes, the old number
   retires (its history appended to the new entry) and the new doctrine
   takes its slot. History event: `doctrine-displaced`.
3. **Load-bearing retirement.** Only if 1 and 2 fail — the candidate is
   genuinely novel. Rank active doctrines by demonstrated load: kill-trigger
   firings + gate invocations + R kill-notes in `history`. The least-loaded
   doctrine is the retirement candidate. A doctrine that has never bound a
   decision is liturgy by Musashi's definition, whatever its theoretical
   elegance. Retirement is never automatic: the merge/displacement analysis
   and the load ranking go to the auditor, who picks. History event:
   `doctrine-retired-for-cap`.

The number seven is not sacred. The auditor may change it — but only
through the same consolidation analysis, on the record. You cannot buy your
way out of "fewer, deeper" with a bigger number.

## R-mandate amendment (2026-09-26, Gabe's directive)

R's charter (`desks/R.md`) gains a standing block: **the doctrine hunt.**

- Every Sunday deep loop, R red-teams ONE doctrine — rotating, nearest
  `revisit_date` first.
- Output is a doctrine kill-note in the same HARD/SOFT/MISS grammar as
  thesis kill-notes, but the target is the *rule*: the strongest mechanism by
  which the doctrine is wrong, obsolete, or actively harmful, with a dated
  event or measurement that would confirm it.
- Every doctrine kill-note is appended to that doctrine's `history` —
  which means the liturgy trigger can never fire on a doctrine R has
  touched. The silence tripwire and the scheduled hunt are complementary:
  the hunt guarantees examination; the tripwire catches what the hunt misses.
- R's kill-precision scoring is unchanged (it scores thesis kills); doctrine
  kill-notes are tracked separately in the doctrine's history. A doctrine
  killed by R's note counts as a MANUAL trigger firing.

## Wiring

- [x] `audit_doctrines.py` wired into the hourly worker's step-0 audit gates
      2026-09-26 ~04:35 CDT (nightwatch skill). Gabe-authorized daylight
      wiring, explicit procedure change, watched run: all four audits exit 0
      (counts consistent, queue schema valid, doctrines clean — no triggers
      fired, no revisits due). Exit-2 = violation contract verified.
- [x] **Doctrine trip circuit breaker compiled 2026-09-26 ~04:45 CDT**
      (Gabe-authorized; trigger scoping approved ~04:33 CDT).
      `bin/trip_doctrines.py` runs in step-0 after the audit: on new
      `kill`-class proposals for D-001/D-003/D-004 it appends their ids to
      `hidden_files/doctrine.trip` (idempotent, exit 0 always). `book_trade.py`
      refuses new risk (book/shadow/bootstrap, exit 4) while the trip file
      is non-empty — same path as `kill.switch`, one added condition;
      `exit`/`audit`/`settle` stay live. Clearing procedure (minds only):
      adjudicate the proposal (reaffirm/revise/retire), fix the enforcement,
      `rm hidden_files/doctrine.trip`, log the resolution `EVENT:` in
      LESSONS.md. `book_trade.py resume` deliberately does NOT clear it.
- [ ] First R doctrine-hunt runs on the first Sunday deep loop after this
      file lands.

## Registry contents

- **D-001** — "Position sizing is computed, never chosen" (`book_trade.py`
  `kelly_size`: quarter-Kelly, floor-to-nickel, $0.10 dust floor, r≤1.0 by
  construction). The Galen candidate. **KILLED 2026-09-30** — K1-bis-F fired
  (EXEMPTION THEATER: 4 trailing-30d F bookings, 100% mikiri-exempt,
  F eff_n=0.0 graded; finding verified, verdict UPHELD by K3N1). The 'by
  construction' claim is struck: the code still computes sizes, but Kelly's
  safety premise (calibrated p's) was never by-construction. Doctrine now
  JUDGMENT_PROSE. Interim regime: F books flat $0.10 until eff_n>=5
  (code-enforced, self-clearing). Full entry in
  `hidden_files/doctrine_registry.json`.
- **D-002** — "Fewer, deeper: the registry cap" (registry holds at most
  seven active doctrines; at cap, entry only via merge, displacement, or
  load-bearing retirement — the consolidation procedure above). Musashi's
  anti-proliferation nerve, installed as machinery. Full entry in
  `hidden_files/doctrine_registry.json`; `max_doctrines: 7` is a
  top-level registry field.
- **D-003** — "No engagement without a read margin (mikiri)" (the static EV
  band is retired: `(win_p − k·σ_desk) − price > 0.05`, σ from
  decay-weighted resolved history; every thesis names the loser and tags
  the initiative — ken_no_sen / tai_no_sen / tai_tai_no_sen; calibration
  graded per desk×sen). Musashi's selection nerve, installed as machinery:
  never fight the unreadable opponent. Cold-start exempt rows are the
  labeled calibration-building duels. Full entry in
  `hidden_files/doctrine_registry.json`.
- **D-004** — "The pre-registered trap (hyoshi)" (the answer to the
  between-hour blindness: the hourly brain reads and pre-registers an
  algorithmic trap in `hidden_files/traps.jsonl`; the 90s hook is only the
  tripwire — it pattern-matches price crossings and executes through
  `book_trade.py`, which re-enforces every gate at the observed price. The
  trigger price is derived, not chosen: the gate's own breakeven. Near-miss
  arming only (margin in (0, 5)pts), full thesis but no size on the trap,
  one-shot, 59-minute fuse, ≤5 armed / ≤1 per market). The trap authorizes
  the attempt, never the outcome. Full entry in
  `hidden_files/doctrine_registry.json`.
