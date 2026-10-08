"""test_driver_gate.py — driver-concentration gate tests.

The operator's flag: 4 of 6 open paper positions shared an Iran/Hormuz macro driver
while the correlation gate only caught same-slug event families. The gate:
--driver required on every booking (framework-owned taxonomy), max 2 open per
driver across M/S/F/Q/C, X shadows exempt (they mirror by design).
Directives are NOT exempt — the cap is absolute;
they still declare --driver for tagging.

Runs ONLY via run_tests.sh (sandboxed HOME). Script resolved from __file__.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testutil

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "book_trade.py")
REAL_TAXONOMY = os.path.join(HERE, "fixtures", "driver_taxonomy.json")
GOAL_SUBPATH = testutil.GOAL_SUBPATH


def setup_taxonomy(home):
    dest = os.path.join(home, GOAL_SUBPATH, "hidden_files",
                        "driver_taxonomy.json")
    shutil.copy(REAL_TAXONOMY, dest)


def book(home, desk, market, family, driver=None, directive=False):
    args = ["book", "--desk", desk, "--market", market, "--side", "no",
            "--price", "20", "--p", "0.5", "--family", family,
            "--loser", "test-loser-crowd", "--sen", "tai_no_sen"]
    if driver is not None:
        args += ["--driver", driver]
    if directive:
        args += ["--directive"]
    return testutil.run_script(home, SCRIPT, *args)


def ledger_rows(home):
    return testutil.read_hidden(home, "book_ledger.jsonl") or []


def open_books(rows):
    return [e for e in rows if e.get("action") == "book"
            and e.get("status") == "open"]


def test_third_same_driver_rejected_naming_blockers():
    """Cap = 2: the M/S-style mirror pair is allowed; a 3rd pile-on REJECTs
 (exit 3) and names the blocking receipt_ids. Rejection is logged."""
    with testutil.isolated_home() as home:
        setup_taxonomy(home)
        r1 = book(home, "F", "test-iran-nuclear-deal-2026", "test-nuclear",
                  "iran-geopolitics")
        assert r1.returncode == 0, r1.stdout + r1.stderr
        r2 = book(home, "S", "test-hormuz-shipping-lanes-2026", "test-shipping",
                  "iran-geopolitics")
        assert r2.returncode == 0, r2.stdout + r2.stderr  # mirror pair OK
        r3 = book(home, "F", "test-tehran-oil-exports-2026", "test-exports",
                  "iran-geopolitics")
        assert r3.returncode == 3, r3.stdout + r3.stderr
        assert "driver-concentration" in r3.stdout, r3.stdout
        rows = open_books(ledger_rows(home))
        ids = [e["receipt_id"] for e in rows]
        assert len(ids) == 2
        for rid in ids:  # both blockers named in the rejection
            assert rid in r3.stdout, f"{rid} not named: {r3.stdout}"
        # the rejection is logged, never silently clipped
        rej = testutil.read_hidden(home, "rejections.jsonl") or []
        assert any("driver-concentration" in (r.get("reason") or "")
                   for r in rej), "rejection not logged"


def test_missing_and_unknown_driver_rejected():
    with testutil.isolated_home() as home:
        setup_taxonomy(home)
        r = book(home, "F", "test-missing-driver-1", "test-fam-1")
        assert r.returncode == 3, r.stdout + r.stderr
        assert "--driver is required" in r.stdout, r.stdout
        r = book(home, "F", "test-unknown-driver-1", "test-fam-2",
                 "not-a-real-driver")
        assert r.returncode == 3, r.stdout + r.stderr
        assert "not in taxonomy" in r.stdout, r.stdout
        assert open_books(ledger_rows(home)) == []


def test_x_shadow_exempt_on_capped_driver():
    """X mirrors by design: a shadow on a driver already at cap is ACCEPTed
 and inherits the source's driver for audit visibility."""
    with testutil.isolated_home() as home:
        setup_taxonomy(home)
        r1 = book(home, "F", "test-iran-nuclear-deal-2026", "test-nuclear",
                  "iran-geopolitics")
        assert r1.returncode == 0, r1.stdout + r1.stderr
        r2 = book(home, "S", "test-hormuz-shipping-lanes-2026", "test-shipping",
                  "iran-geopolitics")
        assert r2.returncode == 0, r2.stdout + r2.stderr
        src = open_books(ledger_rows(home))[0]["receipt_id"]
        r = testutil.run_script(
            home, SCRIPT, "shadow",
            "--market", "test-iran-nuclear-deal-2026", "--side", "no",
            "--price", "20", "--shadow-of", src,
            "--attempted", "20000", "--fill", "1000")
        assert r.returncode == 0, r.stdout + r.stderr
        shadows = [e for e in open_books(ledger_rows(home))
                   if e["desk"] == "X"]
        assert len(shadows) == 1
        assert shadows[0].get("driver") == "iran-geopolitics"


def test_directive_blocked_on_full_driver():
    """The cap is ABSOLUTE: a directive on a full driver
 is REJECTED like any other booking. Directives still declare --driver
 for tagging — the tag is recorded on accepted rows."""
    with testutil.isolated_home() as home:
        setup_taxonomy(home)
        assert book(home, "F", "test-iran-nuclear-deal-2026", "test-nuclear",
                    "iran-geopolitics").returncode == 0
        assert book(home, "S", "test-hormuz-shipping-lanes-2026", "test-shipping",
                    "iran-geopolitics").returncode == 0
        r = book(home, "C", "test-directive-iran-2026", "test-dirfam",
                 "iran-geopolitics", directive=True)
        assert r.returncode != 0, r.stdout + r.stderr
        assert "driver-concentration" in r.stdout + r.stderr
        # accepted directive rows still carry the driver tag
        r2 = book(home, "C", "test-directive-fed-2026", "test-dirfam2",
                  "fed-policy", directive=True)
        assert r2.returncode == 0, r2.stdout + r2.stderr
        rows = open_books(ledger_rows(home))
        d = next(e for e in rows if e.get("directive"))
        assert d.get("driver") == "fed-policy"


def test_missing_taxonomy_fails_closed():
    """No taxonomy file = no verifiable driver = no new risk (exit 3)."""
    with testutil.isolated_home() as home:
        # deliberately do NOT copy the taxonomy
        r = book(home, "F", "test-no-taxonomy-1", "test-fam-1",
                 "iran-geopolitics")
        assert r.returncode == 3, r.stdout + r.stderr
        assert "taxonomy unreadable" in r.stdout, r.stdout
        assert open_books(ledger_rows(home)) == []


def test_accepted_rows_carry_driver():
    rows_seen = []
    with testutil.isolated_home() as home:
        setup_taxonomy(home)
        r = book(home, "C", "another-fed-rate-hike-in-2026", "fed-hike",
                 "fed-policy")
        assert r.returncode == 0, r.stdout + r.stderr
        assert "driver=fed-policy" in r.stdout, r.stdout
        rows_seen = open_books(ledger_rows(home))
    assert len(rows_seen) == 1
    assert rows_seen[0].get("driver") == "fed-policy"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok - {t.__name__}")
        except AssertionError as ex:
            failed += 1
            print(f"NOT OK - {t.__name__}: {ex}")
    sys.exit(1 if failed else 0)
