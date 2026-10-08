"""test_mikiri.py — D-003 confidence-bounded EV gate + thesis schema tests.

The operator's directive: the static p-price band is replaced by
(win_p - k*sigma_desk) - price > 0.05, and every thesis must name the loser
and tag the initiative (ken_no_sen | tai_no_sen | tai_tai_no_sen).

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


def setup(home):
    shutil.copy(REAL_TAXONOMY,
                os.path.join(home, GOAL_SUBPATH, "hidden_files",
                             "driver_taxonomy.json"))


def seed_scored(home, desk, n=6, p=0.7, won=True):
    """Seed n resolved scored rows for desk (recent => weight ~1 each)."""
    rows = [{"desk": desk, "market": f"mikiri-seed-{i}", "side": "yes",
             "p": p, "outcome": 1 if won else 0,
             "brier": round((p - (1 if won else 0)) ** 2, 4),
             "sen": "ken_no_sen", "resolved_cdt": "2026-09-25 12:00",
             "scored_cdt": "2026-09-25 12:00 CDT"}
            for i in range(n)]
    doc = {"pending": [], "scored": rows}
    path = os.path.join(home, GOAL_SUBPATH, "hidden_files", "brier_shadow.json")
    with open(path, "w") as f:
        json.dump(doc, f)


def book(home, desk="M", market="mikiri-test", side="yes", price="60",
         p="0.70", family="mikiri-fam", driver="tech-culture",
         loser="retail momentum chasers", sen="ken_no_sen", extra=()):
    args = ["book", "--desk", desk, "--market", market, "--side", side,
            "--price", price, "--p", p, "--family", family,
            "--driver", driver, "--loser", loser, "--sen", sen]
    args += list(extra)
    return testutil.run_script(home, SCRIPT, *args)


def ledger_rows(home):
    return testutil.read_hidden(home, "book_ledger.jsonl") or []


def rejections(home):
    return testutil.read_hidden(home, "rejections.jsonl") or []


passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    if not cond:
        print(f"FAIL {name}: {detail}")


def test_cold_start_exempt_but_labeled():
    """eff_n=0: static gate applies (today's behavior), receipt tagged
 mikiri_exempt — the calibration-building duel, never silent."""
    with testutil.isolated_home() as home:
        setup(home)
        r = book(home)
        check("t1 cold start ACCEPTs", r.returncode == 0,
              r.stdout + r.stderr)
        rows = [e for e in ledger_rows(home) if e.get("action") == "book"]
        check("t1 one row", len(rows) == 1, str(len(rows)))
        rec = rows[0]
        check("t1 mikiri_exempt tagged", "mikiri_exempt" in rec, str(rec))
        check("t1 loser recorded", rec.get("loser") == "retail momentum chasers",
              str(rec.get("loser")))
        check("t1 sen recorded", rec.get("sen") == "ken_no_sen",
              str(rec.get("sen")))
        check("t1 exempt rows carry no mikiri block",
              "mikiri" not in rec, str(rec.get("mikiri")))


def test_mikiri_rejects_thin_margin():
    """Desk with history (eff_n~6): p=0.70 @ 60c passes the OLD static gate
 (10pt edge) but the k*sigma penalty compresses the margin below the band
 => REJECT with 'mikiri gate', logged."""
    with testutil.isolated_home() as home:
        setup(home)
        seed_scored(home, "M", n=6)
        r = book(home, p="0.70", price="60")
        check("t2 mikiri REJECTs (exit 3)", r.returncode == 3,
              r.stdout + r.stderr)
        check("t2 names the mikiri gate", "mikiri gate" in r.stdout,
              r.stdout)
        check("t2 shows the penalty", "calibration penalty" in r.stdout,
              r.stdout)
        rej = rejections(home)
        check("t2 rejection logged", len(rej) == 1 and "mikiri gate" in rej[0]["reason"],
              str(rej))


def test_mikiri_accepts_wide_margin():
    """Same desk: p=0.92 @ 60c survives the penalty => ACCEPT, receipt
 carries the mikiri audit block."""
    with testutil.isolated_home() as home:
        setup(home)
        seed_scored(home, "M", n=6)
        r = book(home, p="0.92", price="60")
        check("t3 mikiri ACCEPTs", r.returncode == 0, r.stdout + r.stderr)
        rows = [e for e in ledger_rows(home) if e.get("action") == "book"]
        rec = rows[0]
        check("t3 mikiri block recorded",
              isinstance(rec.get("mikiri"), dict)
              and rec["mikiri"].get("eff_n", 0) >= 5
              and rec["mikiri"].get("penalty_pts", 0) > 0,
              str(rec.get("mikiri")))


def test_schema_rejects_unreadable():
    """Missing/evasive loser or bad/missing sen => REJECT (exit 3), logged.
 An unreadable opponent fails validation."""
    cases = [
        ("no loser", dict(loser=None)),
        ("evasive loser", dict(loser="x")),
        ("no sen", dict(sen=None)),
        ("bad sen", dict(sen="yolo")),
    ]
    for name, kw in cases:
        with testutil.isolated_home() as home:
            setup(home)
            args = {"desk": "M", "market": f"mikiri-{name}".replace(" ", "-")}
            for k, v in kw.items():
                if v is not None:
                    args[k] = v
            base = ["book", "--desk", args["desk"], "--market", args["market"],
                    "--side", "yes", "--price", "60", "--p", "0.70",
                    "--family", "mikiri-fam", "--driver", "tech-culture"]
            if "loser" in kw and kw["loser"] is not None:
                base += ["--loser", kw["loser"]]
            elif "loser" not in kw:
                base += ["--loser", "retail momentum chasers"]
            if "sen" in kw and kw["sen"] is not None:
                base += ["--sen", kw["sen"]]
            elif "sen" not in kw:
                base += ["--sen", "ken_no_sen"]
            r = testutil.run_script(home, SCRIPT, *base)
            check(f"t4 {name} REJECTs", r.returncode == 3,
                  r.stdout + r.stderr)
            check(f"t4 {name} cites mikiri", "mikiri" in r.stdout.lower(),
                  r.stdout)
            rej = rejections(home)
            check(f"t4 {name} logged", len(rej) == 1, str(rej))


def test_shadow_inherits_read():
    """X shadows inherit loser/sen from the source — X never names its own."""
    with testutil.isolated_home() as home:
        setup(home)
        r1 = book(home, desk="S", market="mikiri-src", sen="tai_no_sen",
                  loser="panic sellers after the headline")
        assert r1.returncode == 0, r1.stdout + r1.stderr
        rid = [e for e in ledger_rows(home)
               if e.get("action") == "book"][0]["receipt_id"]
        r2 = testutil.run_script(home, SCRIPT, "shadow",
                                "--market", "mikiri-src", "--side", "yes",
                                "--price", "55", "--shadow-of", rid,
                                "--attempted", "20000", "--fill", "100")
        check("t5 shadow ACCEPTs", r2.returncode == 0, r2.stdout + r2.stderr)
        sh = [e for e in ledger_rows(home)
              if e.get("desk") == "X"][0]
        check("t5 shadow inherits loser",
              sh.get("loser") == "panic sellers after the headline",
              str(sh.get("loser")))
        check("t5 shadow inherits sen", sh.get("sen") == "tai_no_sen",
              str(sh.get("sen")))


def test_directive_requires_schema():
    """Directives are EV-exempt but not schema-exempt: the read is still
 declared for tagging."""
    with testutil.isolated_home() as home:
        setup(home)
        r = testutil.run_script(home, SCRIPT, "book", "--desk", "M",
                                "--market", "mikiri-dir", "--side", "yes",
                                "--price", "60", "--p", "0.70",
                                "--family", "mikiri-fam",
                                "--driver", "tech-culture",
                                "--directive")
        check("t6 directive without schema REJECTs", r.returncode == 3,
              r.stdout + r.stderr)
        r2 = book(home, market="mikiri-dir2", extra=("--directive",),
                  loser="the operator's direct order", sen="ken_no_sen")
        check("t6 directive with schema ACCEPTs", r2.returncode == 0,
              r2.stdout + r2.stderr)


def test_sigma_math_spot():
    """sigma(p) = sqrt(p(1-p)/eff_n): spot-check the arithmetic the gate
 relies on (6 recent rows => eff_n in [5.8, 6.0] after 21d decay)."""
    eff = 5.9  # 6 rows scored ~1 day ago: 6 * 0.5**(1/21)
    sig = ((0.7 * 0.3) / eff) ** 0.5
    check("t7 sigma formula sane", 0.18 < sig < 0.20, str(sig))
    margin = (0.70 - 1.0 * sig) - 0.60
    check("t7 thin margin below band", margin < 0.05, str(margin))
    margin2 = (0.92 - 1.0 * (((0.92 * 0.08) / eff) ** 0.5)) - 0.60
    check("t7 wide margin clears band", margin2 > 0.05, str(margin2))


for fn in [test_cold_start_exempt_but_labeled,
           test_mikiri_rejects_thin_margin,
           test_mikiri_accepts_wide_margin,
           test_schema_rejects_unreadable,
           test_shadow_inherits_read,
           test_directive_requires_schema,
           test_sigma_math_spot]:
    fn()

print(f"mikiri: {len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
