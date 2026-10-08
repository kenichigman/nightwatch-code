"""test_traps.py — D-004 pre-registered trap (bounded micro-decision path) tests.

The hyoshi answer: the hourly brain reads, the 90s hook is the tripwire.
These tests verify: arm validation (near-miss bound, direction, proliferation
caps), crossing detection, crash-safe one-shot semantics, expiry, cancel,
volume-gated traps failing closed, settle, and that a trap execution passes
through book_trade.py's full gate (the trap authorizes the attempt, never
the outcome) with trap_id on the receipt.

Runs ONLY via run_tests.sh (sandboxed HOME). Script resolved from __file__.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testutil

HERE = os.path.dirname(os.path.abspath(__file__))
TRAPS = os.path.join(HERE, "bin", "traps.py")
BOOK = os.path.join(HERE, "book_trade.py")
REAL_TAXONOMY = os.path.join(HERE, "fixtures", "driver_taxonomy.json")
REAL_WATCHLIST = os.path.join(HERE, "fixtures", "markets.json")
GOAL_SUBPATH = testutil.GOAL_SUBPATH
DRV = "tech-culture"

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    if not cond:
        print(f"FAIL {name}: {detail}")


def setup(home):
    hf = os.path.join(home, GOAL_SUBPATH, "hidden_files")
    shutil.copy(REAL_TAXONOMY, os.path.join(hf, "driver_taxonomy.json"))
    desks = os.path.join(home, GOAL_SUBPATH, "desks")
    os.makedirs(desks, exist_ok=True)
    shutil.copy(REAL_WATCHLIST, os.path.join(desks, "WATCHLIST.json"))


def wl_key(home):
    with open(os.path.join(home, GOAL_SUBPATH, "desks",
                           "WATCHLIST.json")) as f:
        return sorted(json.load(f)["markets"].keys())[0]


def arm(home, market=None, trigger="below", trigger_px="60", current_px="70",
        margin="2.5", extra=()):
    market = market or wl_key(home)
    args = ["arm", "--desk", "M", "--market", market, "--slug", "trap-slug",
            "--venue", "us", "--side", "yes", "--trigger", trigger,
            "--trigger-px-c", trigger_px, "--current-px-c", current_px,
            "--p", "0.72", "--family", "trap-fam", "--driver", DRV,
            "--loser", "market makers are slow", "--sen", "tai_no_sen",
            "--arming-margin-pts", margin, "--armed-by", "cycle-test"]
    args += list(extra)
    return testutil.run_script(home, TRAPS, *args)


def trap_events(home):
    return testutil.read_hidden(home, "traps.jsonl") or []


def trap_id_of(home, idx=0):
    evs = [e for e in trap_events(home) if e.get("event") == "armed"]
    return evs[idx]["trap_id"] if evs else None


def write_prices(home, mapping):
    p = os.path.join(home, "prices.json")
    with open(p, "w") as f:
        json.dump(mapping, f)
    return p


def check_traps(home, mapping):
    return testutil.run_script(home, TRAPS, "check", "--prices",
                               write_prices(home, mapping))


def armed_ids(home):
    r = testutil.run_script(home, TRAPS, "armed")
    assert r.returncode == 0, r.stdout + r.stderr
    return [e["trap_id"] for e in json.loads(r.stdout)]


# --- arm validation -------------------------------------------------------
def test_arm_valid_and_bounds():
    with testutil.isolated_home() as home:
        setup(home)
        k = wl_key(home)
        r = arm(home, market=k)
        check("t1 valid arm ACCEPTs", r.returncode == 0, r.stdout + r.stderr)
        check("t1 ARMED printed", "ARMED trap-" in r.stdout, r.stdout)
        evs = trap_events(home)
        check("t1 one armed event", len(evs) == 1 and evs[0]["event"] == "armed",
              str(evs))
        check("t1 59-min fuse",
              evs[0]["expiry_cdt"] > evs[0]["armed_cdt"], str(evs[0]))

        # margin already clears the band -> book it directly, never trap it
        r = arm(home, market=k, margin="6.0")
        check("t1 margin>=band REJECTs", r.returncode == 3, r.stdout + r.stderr)
        # negative edge -> lottery ticket, not a near-miss
        r = arm(home, market=k, margin="-1.0")
        check("t1 margin<=0 REJECTs", r.returncode == 3, r.stdout + r.stderr)
        # trigger on the wrong side of current price
        r = arm(home, market=k, trigger="below", trigger_px="80",
                current_px="70")
        check("t1 wrong-direction REJECTs", r.returncode == 3,
              r.stdout + r.stderr)
        # second trap on the same market
        r = arm(home, market=k)
        check("t1 dup-market REJECTs", r.returncode == 3, r.stdout + r.stderr)
        # unreadable opponent cannot be trapped
        r = arm(home, market=k, extra=("--loser", "x"))
        check("t1 evasive loser REJECTs", r.returncode == 3,
              r.stdout + r.stderr)


def test_arm_max_five():
    with testutil.isolated_home() as home:
        setup(home)
        keys = sorted(json.load(open(os.path.join(
            home, GOAL_SUBPATH, "desks", "WATCHLIST.json")))["markets"].keys())
        assert len(keys) >= 6, "need 6 watchlist markets for the cap test"
        for k in keys[:5]:
            r = arm(home, market=k)
            assert r.returncode == 0, r.stdout + r.stderr
        r = arm(home, market=keys[5])
        check("t2 6th trap REJECTs (max 5)", r.returncode == 3,
              r.stdout + r.stderr)
        # unknown market key
        r = arm(home, market="not-a-market")
        check("t2 unknown market REJECTs", r.returncode == 3,
              r.stdout + r.stderr)


# --- crossing / one-shot / expiry ------------------------------------------
def test_crossing_and_oneshot():
    with testutil.isolated_home() as home:
        setup(home)
        k = wl_key(home)
        r = arm(home, market=k, trigger_px="60", current_px="70")
        assert r.returncode == 0, r.stdout + r.stderr
        tid = trap_id_of(home)

        # no cross: still above the tripwire
        r = check_traps(home, {k: {"px": 0.65, "prev_px": 0.70}})
        check("t3 no-cross silent", r.returncode == 0 and r.stdout.strip() == "",
              r.stdout + r.stderr)
        check("t3 still armed", tid in armed_ids(home),
              "armed set lost the trap")

        # crossing: prev above, now at/below the wire
        r = check_traps(home, {k: {"px": 0.59, "prev_px": 0.65}})
        check("t3 cross emits directive", r.returncode == 0 and tid in r.stdout,
              r.stdout + r.stderr)
        d = json.loads(r.stdout.strip())
        check("t3 directive carries observed price",
              d["price_c"] == 59.0, str(d))
        check("t3 directive carries the thesis",
              d["loser"] == "market makers are slow"
              and d["sen"] == "tai_no_sen" and d["p"] == 0.72, str(d))
        evs = trap_events(home)
        trig = [e for e in evs if e.get("event") == "triggered"]
        check("t3 triggered claimed in the log",
              len(trig) == 1 and trig[0]["trap_id"] == tid, str(evs))

        # refire: the trap is consumed — the hook can never double-fire
        r = check_traps(home, {k: {"px": 0.50, "prev_px": 0.59}})
        check("t3 refire silent (one-shot)", r.stdout.strip() == "",
              r.stdout + r.stderr)
        evs = trap_events(home)
        check("t3 exactly one triggered event",
              len([e for e in evs if e.get("event") == "triggered"]) == 1,
              str(evs))


def test_above_trigger_and_expiry_and_cancel():
    with testutil.isolated_home() as home:
        setup(home)
        k = wl_key(home)
        r = arm(home, market=k, trigger="above", trigger_px="80",
                current_px="70")
        assert r.returncode == 0, r.stdout + r.stderr
        tid = trap_id_of(home)
        r = check_traps(home, {k: {"px": 0.81, "prev_px": 0.79}})
        check("t4 above-cross fires", tid in r.stdout, r.stdout + r.stderr)

        # cancel path
        keys = sorted(json.load(open(os.path.join(
            home, GOAL_SUBPATH, "desks", "WATCHLIST.json")))["markets"].keys())
        k2 = keys[1]
        r = arm(home, market=k2)
        assert r.returncode == 0
        tid2 = [t for t in
                [e["trap_id"] for e in trap_events(home)
                 if e.get("event") == "armed"] if t != tid][0]
        r = testutil.run_script(home, TRAPS, "cancel", "--trap-id", tid2,
                                "--reason", "thesis died", "--by", "cycle-2")
        check("t4 cancel ACCEPTs", r.returncode == 0, r.stdout + r.stderr)
        r = check_traps(home, {k2: {"px": 0.10, "prev_px": 0.90}})
        check("t4 cancelled trap never fires", r.stdout.strip() == "",
              r.stdout)


def test_volume_gated_trap_fails_closed():
    """A trap armed WITH min_volume_24h is unevaluable in v1 (the hook's
 data plane carries no volume) — it must stay armed, never silently
 degrade to price-only."""
    with testutil.isolated_home() as home:
        setup(home)
        k = wl_key(home)
        r = arm(home, market=k, extra=("--min-volume-24h", "10000"))
        assert r.returncode == 0, r.stdout + r.stderr
        tid = trap_id_of(home)
        r = check_traps(home, {k: {"px": 0.50, "prev_px": 0.70}})
        check("t5 volume trap does not fire", r.stdout.strip() == "",
              r.stdout + r.stderr)
        evs = trap_events(home)
        check("t5 stays armed (no triggered/expired)",
              not [e for e in evs if e.get("event") in
                   ("triggered", "expired")],
              str(evs))


# --- execution through the fortress ----------------------------------------
def test_trap_execution_regated_and_tagged():
    """The trap authorizes the attempt; book_trade.py decides. A directive
 whose execution price fails the gate REJECTs through the logged path,
 and an ACCEPT carries trap_id on the receipt."""
    with testutil.isolated_home() as home:
        setup(home)
        k = wl_key(home)
        r = arm(home, market=k, trigger_px="60", current_px="70", margin="2.5")
        assert r.returncode == 0
        tid = trap_id_of(home)
        r = check_traps(home, {k: {"px": 0.59, "prev_px": 0.65}})
        d = json.loads(r.stdout.strip())

        # cold-start static band is 5pt: p=0.72 @ 59c = 13pt edge -> ACCEPTs
        b = testutil.run_script(
            home, BOOK, "book", "--desk", d["desk"], "--market", "trap-exec",
            "--side", d["side"], "--price", str(d["price_c"]), "--p", str(d["p"]),
            "--family", d["family"], "--driver", d["driver"],
            "--loser", d["loser"], "--sen", d["sen"], "--trap-id", d["trap_id"],
            "--note", d["note"], "--confirm-cents")
        check("t6 trap execution ACCEPTs when gate clears", b.returncode == 0,
              b.stdout + b.stderr)
        rows = [e for e in (testutil.read_hidden(home, "book_ledger.jsonl") or [])
                if e.get("action") == "book"]
        check("t6 receipt carries trap_id",
              rows and rows[-1].get("trap_id") == tid, str(rows[-1] if rows else None))

        # ...but a price that fails the gate at execution REJECTs: the trap
        # cannot smuggle a booking past the fortress.
        b = testutil.run_script(
            home, BOOK, "book", "--desk", "M", "--market", "trap-exec2",
            "--side", "yes", "--price", "71", "--p", "0.72",
            "--family", "trap-fam2", "--driver", DRV,
            "--loser", "market makers are slow", "--sen", "tai_no_sen",
            "--trap-id", tid, "--confirm-cents")
        check("t6 execution REJECTs when gate fails", b.returncode == 3,
              b.stdout + b.stderr)

        # settle records the verdict in the trap log
        s = testutil.run_script(home, TRAPS, "settle", "--trap-id", tid,
                                "--result", "accept", "--receipt", "bk-x",
                                "--detail", "script ACCEPT")
        check("t6 settle ACCEPTs", s.returncode == 0, s.stdout + s.stderr)
        evs = trap_events(home)
        st = [e for e in evs if e.get("event") == "trap_settled"]
        check("t6 trap_settled logged",
              len(st) == 1 and st[0]["result"] == "accept"
              and st[0]["receipt_id"] == "bk-x", str(evs))


def test_side_native_no_trap():
    # Regression: the first live trap (side=no, below 83.5c)
    # expired untriggerable because cmd_check compared the hook's Yes-side
    # px against the No-side threshold with no side conversion. Trap arm
    # semantics are side-native; the check must convert.
    with testutil.isolated_home() as home:
        setup(home)
        k = wl_key(home)
        r = arm(home, market=k, trigger="below", trigger_px="83.5",
                current_px="84", margin="4.5", extra=("--side", "no"))
        assert r.returncode == 0, r.stdout + r.stderr
        tid = trap_id_of(home)

        # No 85 -> 84.5 (Yes 15 -> 15.5): still above the wire, silent
        r = check_traps(home, {k: {"px": 0.155, "prev_px": 0.15}})
        check("t7 no-side no-cross silent", r.returncode == 0
              and r.stdout.strip() == "", r.stdout + r.stderr)
        check("t7 no-side still armed", tid in armed_ids(home),
              "armed set lost the trap")

        # No 85 -> 83 (Yes 15 -> 17): crosses below 83.5 on the No side
        r = check_traps(home, {k: {"px": 0.17, "prev_px": 0.15}})
        check("t7 no-side cross emits directive",
              r.returncode == 0 and tid in r.stdout, r.stdout + r.stderr)
        d = json.loads(r.stdout.strip())
        check("t7 directive price is side-native (No cents)",
              d["price_c"] == 83.0, str(d))
        check("t7 directive carries the side",
              d["side"] == "no", str(d))
        evs = trap_events(home)
        check("t7 triggered claimed in the log",
              len([e for e in evs if e.get("event") == "triggered"]) == 1,
              str(evs))

        # refire: consumed, one-shot
        r = check_traps(home, {k: {"px": 0.20, "prev_px": 0.17}})
        check("t7 refire silent (one-shot)", r.stdout.strip() == "",
              r.stdout + r.stderr)


def main():
    test_arm_valid_and_bounds()
    test_arm_max_five()
    test_crossing_and_oneshot()
    test_above_trigger_and_expiry_and_cancel()
    test_volume_gated_trap_fails_closed()
    test_trap_execution_regated_and_tagged()
    test_side_native_no_trap()
    print(f"test_traps: {len(passed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
