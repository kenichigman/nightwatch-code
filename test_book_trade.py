#!/usr/bin/env python3
"""test_book_trade.py — regression tests for the Nightwatch booking gate.

Gabe's locked work (2026-09-28): booking regression tests required, and
cents/dollars ambiguity impossible by construction.

Every test runs against a tmp dir (all of book_trade's path constants are
repointed in setUp) — the real ledger, worker_state, and hook files are
never touched.

Run:  python3 test_book_trade.py
"""
import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone

GOAL = os.path.expanduser("~/workspace/goals/10-polymarket-experiment")
sys.path.insert(0, GOAL)
import book_trade as bt  # noqa: E402


def fresh_heartbeat():
    return {"last_tick": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fetch_ok": 5, "fetch_fail": 0}


class BookTradeTestBase(unittest.TestCase):
    """Repoints every filesystem dependency of book_trade at a tmp dir."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self._orig = {}
        paths = {
            "ROOT": t,
            "LEDGER": f"{t}/hidden_files/book_ledger.jsonl",
            "WS_PATH": f"{t}/hidden_files/worker_state.json",
            "KILL_SWITCH": f"{t}/hidden_files/kill.switch",
            "DOCTRINE_TRIP": f"{t}/hidden_files/doctrine.trip",
            "HOOK_PRICES": f"{t}/hooks/nightwatch-prices.json",
            "HOOK_STATUS": f"{t}/hooks/nightwatch-status.json",
            "RESOLVE_REVIEW": f"{t}/hidden_files/resolution_review.jsonl",
            "WATCHLIST_PATH": f"{t}/desks/WATCHLIST.json",
            "REJECTIONS": f"{t}/hidden_files/rejections.jsonl",
            "SETTLED_PATH": f"{t}/hidden_files/settled.json",
            "DRIVER_TAXONOMY_PATH": f"{t}/hidden_files/driver_taxonomy.json",
            "INTERIM_PATH": f"{t}/hidden_files/doctrine_interim.json",
            "BRIER_SHADOW": f"{t}/hidden_files/brier_shadow.json",
            "FUNNEL_CACHE": f"{t}/hidden_files/funnel_cache.json",
            "DECISION_FEATURES": f"{t}/hidden_files/decision_features.jsonl",
            "STATUS_PATH": f"{t}/desks/STATUS.md",
        }
        for k, v in paths.items():
            self._orig[k] = getattr(bt, k)
            setattr(bt, k, v)
        self._orig_sw = bt.stream_watch
        bt.stream_watch = None  # unit tests decide locally; no supervisor

        os.makedirs(f"{t}/hidden_files", exist_ok=True)
        os.makedirs(f"{t}/desks", exist_ok=True)
        os.makedirs(f"{t}/hooks", exist_ok=True)
        drivers = {f"d{i}": {} for i in range(1, 9)}
        drivers["test-driver"] = {}
        with open(f"{t}/hidden_files/driver_taxonomy.json", "w") as f:
            json.dump({"drivers": drivers}, f)
        with open(f"{t}/hooks/nightwatch-status.json", "w") as f:
            json.dump(fresh_heartbeat(), f)
        with open(f"{t}/hooks/nightwatch-prices.json", "w") as f:
            json.dump({"mkt-a": {"px": 0.87},
                       "mkt-sub": {"px": 0.008},
                       "mkt-low": {"px": 0.05}}, f)
        with open(f"{t}/desks/WATCHLIST.json", "w") as f:
            json.dump({"markets": {"mkt-a": {"slug": "mkt-a"},
                                   "mkt-sub": {"slug": "mkt-sub"},
                                   "mkt-low": {"slug": "mkt-low"}}}, f)
        with open(f"{t}/hidden_files/settled.json", "w") as f:
            json.dump({"settled": {}}, f)
        with open(f"{t}/hidden_files/brier_shadow.json", "w") as f:
            json.dump({"pending": [], "scored": []}, f)  # cold start: sigma None
        with open(f"{t}/hidden_files/worker_state.json", "w") as f:
            json.dump({}, f)
        # Honest-fill stub (2026-10-06): cmd_book/cmd_shadow/cmd_exit walk a
        # live book; tests inject snapshots via NIGHTWATCH_BOOK_STUB instead.
        # set_book() writes a deep two-sided book at price_c for a market.
        self._book_stub_path = f"{t}/book_stub.json"
        with open(self._book_stub_path, "w") as f:
            json.dump({}, f)
        self._old_book_stub = os.environ.get("NIGHTWATCH_BOOK_STUB")
        os.environ["NIGHTWATCH_BOOK_STUB"] = self._book_stub_path

    def tearDown(self):
        for k, v in self._orig.items():
            setattr(bt, k, v)
        bt.stream_watch = self._orig_sw
        if self._old_book_stub is None:
            os.environ.pop("NIGHTWATCH_BOOK_STUB", None)
        else:
            os.environ["NIGHTWATCH_BOOK_STUB"] = self._old_book_stub
        self.tmp.cleanup()

    def set_book(self, market, price_c, venue="com", tags=("geopolitics",),
                 depth_usd=1e9, spread_c=1.0):
        """Deep two-sided stub book at price_c (fee-free geopolitics default
        keeps legacy P&L assertions stable; pass tags=("sports",) to test
        fees). depth_usd sizes each side's total; spread_c separates touch."""
        p = price_c / 100.0
        bid_p = max(p - spread_c / 100.0, 0.01)
        # Ask touch == limit: fills at the worker's price by construction.
        # One fat level per side: VWAP == touch, depth_1c covers everything.
        snap = {"venue": venue, "tags": list(tags),
                "asks": [[p, depth_usd / p]],
                "bids": [[bid_p, depth_usd / bid_p]]}
        with open(self._book_stub_path) as f:
            all_snaps = json.load(f)
        all_snaps[market] = snap
        with open(self._book_stub_path, "w") as f:
            json.dump(all_snaps, f)

    # -- helpers ---------------------------------------------------------
    def book_ns(self, **kw):
        d = dict(desk="M", market="mkt-a", side="yes", price=13.0, p=0.6,
                 family="", driver="test-driver", loser="market makers wrong",
                 sen="ken_no_sen", directive=False, note="", thesis="t",
                 ev_gate="originated", trap_id="", funnel_event="",
                 nominate_real=False, r_rating=None, proposer="",
                 size_suggest=None, confirm_cents=False)
        d.update(kw)
        return argparse.Namespace(**d)

    def quiet(self, fn, *args):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            code = fn(*args)
        return code, buf.getvalue()

    def rejections(self):
        p = bt.REJECTIONS
        if not os.path.isfile(p):
            return []
        with open(p) as f:
            return [json.loads(l) for l in f if l.strip()]


class TestParsePriceCents(unittest.TestCase):
    """The single choke point: unit tests need no fixtures."""

    def test_accepts(self):
        self.assertEqual(bt.parse_price_cents(87), 87.0)
        self.assertEqual(bt.parse_price_cents(87.5), 87.5)   # half-cent real
        self.assertEqual(bt.parse_price_cents(0.8), 0.8)     # sub-cent real
        self.assertEqual(bt.parse_price_cents("87"), 87.0)

    def test_rejects(self):
        for bad in (0, -5, 100, 8700, "abc", None, ""):
            with self.assertRaises(ValueError, msg=f"raw={bad!r}"):
                bt.parse_price_cents(bad)


class TestUnitTripwire(BookTradeTestBase):
    """The 100x dollars-passing error is caught; real prices are not."""

    def test_book_dollars_rejected(self):
        # mkt-a cached at 87c; 0.87 can only be dollars-as-cents.
        code, out = self.quiet(bt.cmd_book, self.book_ns(price=0.87))
        self.assertEqual(code, 3)
        self.assertIn("DOLLARS", out)
        reasons = [r["reason"] for r in self.rejections()]
        self.assertTrue(any("DOLLARS" in r for r in reasons),
                        "rejections are logged, never silently clipped")

    def test_book_cents_accepted(self):
        self.set_book("mkt-a", 87.0)
        code, _ = self.quiet(bt.cmd_book, self.book_ns(price=87.0, p=0.99))
        self.assertEqual(code, 0)

    def test_book_subcent_longshot_not_flagged(self):
        # mkt-sub cached at ~1c; 0.8c is a genuine longshot price.
        self.set_book("mkt-sub", 0.8)
        code, _ = self.quiet(
            bt.cmd_book, self.book_ns(market="mkt-sub", price=0.8, p=0.6))
        self.assertEqual(code, 0)

    def test_book_no_poller_quote_fails_closed(self):
        # Off-watchlist market: units unverifiable — new risk is never
        # booked blind. (2026-09-28 repair #2: was fail-open.)
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(market="mkt-offlist", price=0.87, p=0.6))
        self.assertEqual(code, 3)
        self.assertIn("unverifiable", out)

    def test_book_no_poller_quote_confirm_cents(self):
        # The operator's explicit unit assertion re-opens the path.
        self.set_book("mkt-offlist", 0.87)
        code, _ = self.quiet(
            bt.cmd_book, self.book_ns(market="mkt-offlist", price=0.87, p=0.6,
                                      confirm_cents=True))
        self.assertEqual(code, 0)

    def test_book_dollars_rejected_low_price(self):
        # THE repair-#2 hole: mkt-low quotes 5c; 0.05 used to pass inside
        # the old 10c direct-match tolerance. The 100x reading wins now.
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(market="mkt-low", price=0.05, p=0.6))
        self.assertEqual(code, 3)
        self.assertIn("DOLLARS", out)

    def test_book_low_price_cents_accepted(self):
        self.set_book("mkt-low", 5.0)
        code, _ = self.quiet(
            bt.cmd_book, self.book_ns(market="mkt-low", price=5.0, p=0.99))
        self.assertEqual(code, 0)

    def test_book_ambiguity_rejected(self):
        # mkt-sub quotes 1c; 0.01 reads as 0.01c OR $0.01 (= 1c) — genuinely
        # ambiguous, rejected until the operator asserts the unit.
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(market="mkt-sub", price=0.01, p=0.6))
        self.assertEqual(code, 3)
        self.assertIn("AMBIGUOUS", out)

    def test_book_ambiguity_confirm_cents(self):
        self.set_book("mkt-sub", 0.01)
        code, _ = self.quiet(
            bt.cmd_book, self.book_ns(market="mkt-sub", price=0.01, p=0.6,
                                      confirm_cents=True))
        self.assertEqual(code, 0)

    def test_book_dollars_not_overridable(self):
        # The smoking gun stands even with explicit confirmation — 0.87
        # against an 87c quote is dollars, full stop.
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(price=0.87, confirm_cents=True))
        self.assertEqual(code, 3)
        self.assertIn("DOLLARS", out)

    def test_book_range_still_rejects(self):
        code, _ = self.quiet(bt.cmd_book, self.book_ns(price=8700))
        self.assertEqual(code, 3)
        code, _ = self.quiet(bt.cmd_book, self.book_ns(price=0))
        self.assertEqual(code, 3)

    def _book_source(self, market="mkt-a", price=87.0, p=0.99):
        # X never shadows directives, so the shadow source is a real booking.
        self.set_book(market, price)
        ns = self.book_ns(market=market, price=price, p=p, directive=False)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        entries = bt.load_ledger()
        return entries[-1]["receipt_id"]

    def _book_directive(self, market="mkt-a", price=87.0):
        self.set_book(market, price)
        ns = self.book_ns(market=market, price=price, directive=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        return bt.load_ledger()[-1]["receipt_id"]

    def test_shadow_dollars_rejected(self):
        rid = self._book_source()
        ns = argparse.Namespace(side="yes", price=0.87, shadow_of=rid,
                                attempted=20000.0,
                                note="", thesis="t")
        code, out = self.quiet(bt.cmd_shadow, ns)
        self.assertEqual(code, 3)
        self.assertIn("DOLLARS", out)

    def test_shadow_cents_accepted(self):
        rid = self._book_source()
        ns = argparse.Namespace(side="yes", price=87.0, shadow_of=rid,
                                attempted=20000.0,
                                note="", thesis="t")
        code, _ = self.quiet(bt.cmd_shadow, ns)
        self.assertEqual(code, 0)

    def test_exit_dollars_rejected(self):
        rid = self._book_directive()
        ns = argparse.Namespace(receipt=rid, exit_price=0.87,
                                auto_price=False, note="")
        code, out = self.quiet(bt.cmd_exit, ns)
        self.assertEqual(code, 3)
        self.assertIn("DOLLARS", out)

    def test_exit_cents_accepted(self):
        rid = self._book_directive()
        ns = argparse.Namespace(receipt=rid, exit_price=80.0,
                                auto_price=False, note="")
        code, _ = self.quiet(bt.cmd_exit, ns)
        self.assertEqual(code, 0)

    def test_exit_no_poller_quote_stays_open(self):
        # Deliberate asymmetry (repair #2): a dark feed never blocks
        # loss-capping. Book off-watchlist with --confirm-cents, exit
        # without a quote — the exit proceeds on the operator's assertion.
        self.set_book("mkt-offlist", 87.0)
        ns = self.book_ns(market="mkt-offlist", price=87.0, p=0.99,
                          directive=True, confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        rid = bt.load_ledger()[-1]["receipt_id"]
        # Darken the book mid-test: the exit must still proceed fail-open.
        with open(self._book_stub_path, "w") as f:
            json.dump({}, f)
        ns = argparse.Namespace(receipt=rid, exit_price=80.0,
                                auto_price=False, note="")
        code, _ = self.quiet(bt.cmd_exit, ns)
        self.assertEqual(code, 0)
        rec = [e for e in bt.load_ledger()
               if e.get("action") == "exit" and e["receipt_id"] == rid][0]
        self.assertEqual(rec["exit_basis"], "unverifiable")


class TestKellyConstruction(unittest.TestCase):
    """Sizing is math, not judgment: gates refuse, Kelly sizes."""

    def test_sizes_when_gate_clears(self):
        size, edge_pts, win_p = bt.kelly_size("yes", 13.0, 0.6, 10.0, 1.0,
                                              0.25, None)
        self.assertEqual(size, 1.0)          # capped: 1.35 -> cap 1.0
        self.assertAlmostEqual(edge_pts, 47.0)
        self.assertEqual(win_p, 0.6)

    def test_ev_gate_refuses(self):
        size, edge_pts, _ = bt.kelly_size("yes", 87.0, 0.6, 10.0, 1.0,
                                          0.25, None)
        self.assertIsNone(size)
        self.assertLess(edge_pts, 5.0)

    def test_gate_boundary_refuses(self):
        # margin 4pts <= 5pt band — NO BET.
        size, _, _ = bt.kelly_size("yes", 95.0, 0.99, 10.0, 1.0, 0.25, None)
        self.assertIsNone(size)

    def test_dust_refuses(self):
        # Gate clears (6pts) but the stake is below $0.10 — NO BET.
        size, _, _ = bt.kelly_size("yes", 50.0, 0.56, 1.0, 10.0, 0.25, None)
        self.assertIsNone(size)

    def test_nickel_floor(self):
        size, _, _ = bt.kelly_size("yes", 40.0, 0.8, 10.0, 10.0, 0.25, None)
        self.assertEqual(size, 1.65)        # 1.6667 floored, never rounded up

    def test_r_le_1_structural(self):
        # No parameter combination may size above fraction*bankroll.
        for price_c in (5.0, 13.0, 50.0, 87.0):
            for p in (0.55, 0.7, 0.9):
                size, _, _ = bt.kelly_size("yes", price_c, p, 10.0, 100.0,
                                           0.25, None)
                if size is not None:
                    self.assertLessEqual(size, 0.25 * 10.0)

    def test_nickel_never_exceeds_raw(self):
        # Repair #2: int(round(size*100)) rounded UP half a cent before the
        # nickel floor — raw $1.046 became $1.05 (above raw). Exact floor now.
        size, _, _ = bt.kelly_size("yes", 50.0, 0.7092, 10.0, 10.0, 0.25, None)
        # raw = ((0.7092-0.5)/0.5) * 0.25 * 10 = 1.046
        self.assertEqual(size, 1.00)
        self.assertLessEqual(size, 1.046)

    def test_dust_boundary_not_rounded_up(self):
        # raw $0.0975 used to round to $0.10 and sneak past the dust line.
        size, _, _ = bt.kelly_size("yes", 50.0, 0.695, 1.0, 10.0, 0.25, None)
        self.assertIsNone(size)

    def test_exact_cap_not_shaved(self):
        # The original 2026-09-28 bug: $1.00 floored to $0.95 by binary
        # float error. Exact integer-cent math keeps it at $1.00.
        size, _, _ = bt.kelly_size("yes", 13.0, 0.6, 10.0, 1.0, 0.25, None)
        self.assertEqual(size, 1.0)

    def test_nickel_granularity_sweep(self):
        # Every emitted size is an exact multiple of $0.05, never above cap.
        for price_c in (5.0, 13.0, 40.0, 50.0, 87.0):
            for p in (0.55, 0.6, 0.7092, 0.8, 0.9, 0.99):
                for side in ("yes", "no"):
                    size, _, _ = bt.kelly_size(side, price_c, p, 10.0, 1.0,
                                               0.25, None)
                    if size is not None:
                        cents = round(size * 100)
                        self.assertAlmostEqual(size * 100, cents, places=6)
                        self.assertEqual(cents % 5, 0)
                        self.assertLessEqual(size, 1.0)


class TestHardGates(BookTradeTestBase):
    """Kill switch, caps, correlation, settlement immutability."""

    def _directive(self, desk="M", market="mkt-a", driver="test-driver",
                   price=13.0):
        # confirm_cents: these gates are tested with off-watchlist markets;
        # the unit assertion keeps each test focused on its own gate.
        self.set_book(market, price)
        ns = self.book_ns(desk=desk, market=market, price=price,
                          driver=driver, directive=True, confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        return bt.load_ledger()[-1]["receipt_id"]

    def _main(self, *argv):
        old = sys.argv
        sys.argv = ["book_trade.py", *argv]
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                ret = bt.main()   # kill path RETURNS 4; dispatch path sys.exits
        except SystemExit as e:
            return e.code
        finally:
            sys.argv = old
        return ret

    def test_kill_blocks_book_not_exit(self):
        rid = self._directive(market="mkt-k1")
        self.quiet(bt.cmd_kill, argparse.Namespace(reason="test"))
        code = self._main("book", "--desk", "M", "--market", "mkt-k2",
                          "--side", "yes", "--price", "13", "--p", "0.6",
                          "--family", "", "--driver", "test-driver",
                          "--loser", "xxxx", "--sen", "ken_no_sen",
                          "--directive")
        self.assertEqual(code, 4)
        # exit stays live: flatten, don't freeze.
        code = self._main("exit", "--receipt", rid, "--exit-price", "80")
        self.assertEqual(code, 0)
        self.quiet(bt.cmd_resume, argparse.Namespace())

    def test_open_cap(self):
        words = ["alpha", "beta", "gamma", "delta",
                 "eps", "zeta", "eta", "theta"]
        for i, w in enumerate(words):
            self._directive(market=f"capmkt-{w}", driver=f"d{i + 1}")
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(market="capmkt-iota", driver="d1",
                                      price=13.0, directive=True,
                                      confirm_cents=True))
        self.assertEqual(code, 3)
        self.assertIn("max 8", out)

    def test_daily_new_cap(self):
        words = ["alpha", "beta", "gamma"]
        for i, w in enumerate(words):
            self.set_book(f"daymkt-{w}", 13.0)
            ns = self.book_ns(market=f"daymkt-{w}", driver=f"d{i + 1}",
                              price=13.0, p=0.6, confirm_cents=True)
            code, _ = self.quiet(bt.cmd_book, ns)
            self.assertEqual(code, 0)
        self.set_book("daymkt-delta", 13.0)
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(market="daymkt-delta", driver="d4",
                                      price=13.0, p=0.6, confirm_cents=True))
        self.assertEqual(code, 3)
        self.assertIn("daily new-trade cap", out)

    def test_correlation_one_per_family(self):
        self._directive(market="corrmkt-alpha")
        self.set_book("corrmkt-alpha-2", 13.0)
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(market="corrmkt-alpha-2",
                                      driver="d2", directive=True,
                                      confirm_cents=True))
        self.assertEqual(code, 3)
        self.assertIn("already open", out)

    def test_settle_immutable(self):
        self._directive(market="setmkt")
        ns = argparse.Namespace(market="setmkt", outcome="YES", pnl=None,
                                evidence="test", resolved_cdt="", note="")
        code, _ = self.quiet(bt.cmd_settle, ns)
        self.assertEqual(code, 0)
        code, out = self.quiet(bt.cmd_settle, ns)
        self.assertEqual(code, 3)
        self.assertIn("immutable", out)


class TestXExploration(BookTradeTestBase):
    """X exploration account (2026-10-05 recharter): originates freely, no
    EV gate; honesty gates (price units, settled universe, driver taxonomy,
    thesis schema) still bind; family/driver caps do not."""

    def _xbook(self, **kw):
        d = dict(desk="X", market="xmkt-alpha", side="yes", price=50.0,
                 p=0.51, driver="test-driver", loser="market makers wrong",
                 sen="ken_no_sen", confirm_cents=True)
        d.update(kw)
        self.set_book(d["market"], d["price"])
        ns = self.book_ns(**d)
        return self.quiet(bt.cmd_book, ns)

    def test_x_books_below_ev_gate(self):
        # 1pt edge: the gated desks refuse; X explores.
        code, out = self._xbook()
        self.assertEqual(code, 0)
        rec = bt.load_ledger()[-1]
        self.assertEqual(rec["desk"], "X")
        # Breadth-first (2026-10-06): $2k depth-capped target, not $20k flat.
        self.assertEqual(rec["size_usd"], 2000.0)
        self.assertEqual(rec["attempted_usd"], 2000.0)
        self.assertEqual(rec["unfilled_usd"], 0.0)
        self.assertIn("fee_usd", rec)
        self.assertIn("depth_1c_usd", rec)
        self.assertTrue(rec.get("explore"))
        self.assertEqual(rec["ev_gate"], "explore")
        self.assertNotIn("mikiri", rec)

    def test_gated_desk_still_refuses(self):
        ns = self.book_ns(market="xmkt-beta", price=50.0, p=0.51,
                          confirm_cents=True)
        code, out = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 3)
        self.assertIn("5pt band", out)

    def test_x_honesty_gates_bind(self):
        # Thesis schema still binds X: no unnamed loser.
        code, out = self._xbook(market="xmkt-gamma", loser="")
        self.assertEqual(code, 3)
        self.assertIn("mikiri", out)
        # Driver taxonomy still binds X.
        code, out = self._xbook(market="xmkt-delta", driver="nope")
        self.assertEqual(code, 3)
        self.assertIn("taxonomy", out)

    def test_x_driver_cap_exempt(self):
        # Fill the driver cap (2) with M directives; X still explores it.
        for mkt in ("xdrv-alpha", "xdrv-beta"):
            self.set_book(mkt, 13.0)
            ns = self.book_ns(market=mkt, driver="test-driver",
                              directive=True, confirm_cents=True)
            code, _ = self.quiet(bt.cmd_book, ns)
            self.assertEqual(code, 0)
        code, _ = self._xbook(market="xmkt-epsilon")
        self.assertEqual(code, 0)

    def test_x_family_cap_exempt(self):
        # M holds family 'xdrv-alpha'; X explores the same family freely.
        self.set_book("xdrv-alpha", 13.0)
        ns = self.book_ns(market="xdrv-alpha", driver="d1",
                          directive=True, confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        code, _ = self._xbook(market="xdrv-alpha-2", driver="d2")
        self.assertEqual(code, 0)

    def test_x_daily_cap_binds(self):
        for i in range(50):
            code, _ = self._xbook(market=f"xcap-{i}", driver=f"d{(i % 8) + 1}")
            self.assertEqual(code, 0)
        code, out = self._xbook(market="xcap-50", driver="d1")
        self.assertEqual(code, 3)
        self.assertIn("daily new-trade cap", out)


class TestHonestFills(BookTradeTestBase):
    """2026-10-06: the book walk replaces the 0.5c haircut. Entries fail
    closed without a depth snapshot; clips are depth-capped at 1c of touch;
    taker fees are modeled and deducted."""

    def test_no_snapshot_refuses_entry(self):
        # Stub is empty: no honest fill exists — fail closed, never assumed.
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(market="nosuch", price=50.0, p=0.6,
                                      directive=True, confirm_cents=True))
        self.assertEqual(code, 3)
        self.assertIn("honest-fill", out)
        reasons = [r["reason"] for r in self.rejections()]
        self.assertTrue(any("honest-fill" in r for r in reasons))

    def test_touch_above_limit_refuses(self):
        # Book touch 60c against a 50c limit: nothing fills within limit.
        self.set_book("limmkt", 60.0)
        code, out = self.quiet(
            bt.cmd_book, self.book_ns(market="limmkt", price=50.0, p=0.6,
                                      directive=True, confirm_cents=True))
        self.assertEqual(code, 3)
        self.assertIn("within limit", out)

    def test_large_clip_slippage_on_thin_book(self):
        # Guaranteed-binding engine test (N1K3, 2026-10-06): a $2000 X clip
        # against a thin three-level book must show slippage — VWAP worse
        # than the touch — independent of what live fills look like.
        snap = {"venue": "us", "tags": ["geopolitics"],
                "asks": [[0.50, 200.0], [0.505, 200.0], [0.51, 200.0]],
                "bids": [[0.49, 100000.0]]}
        with open(self._book_stub_path) as f:
            all_snaps = json.load(f)
        all_snaps["slipmkt"] = snap
        with open(self._book_stub_path, "w") as f:
            json.dump(all_snaps, f)
        ns = self.book_ns(desk="X", market="slipmkt", price=52.0, p=0.6,
                          driver="test-driver", loser="mm wrong",
                          sen="ken_no_sen", confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        rec = bt.load_ledger()[-1]
        # $303 within 1c of the 50c touch fills; the rest is unfilled.
        self.assertAlmostEqual(rec["size_usd"], 303.0, places=1)
        self.assertAlmostEqual(rec["unfilled_usd"], 1697.0, places=1)
        # Slippage appears: VWAP 50.5c > 50c touch, still <= the 52c limit.
        self.assertGreater(rec["price_c"], 50.0)
        self.assertAlmostEqual(rec["price_c"], 50.5, places=2)
        self.assertLessEqual(rec["price_c"], 52.0)

    def test_depth_cap_binds(self):
        # Thin book: $30 within 1c of a 50c touch on a $2000 X clip.
        self.set_book("thinmkt", 50.0, tags=("sports",), depth_usd=30.0)
        ns = self.book_ns(desk="X", market="thinmkt", price=50.0, p=0.6,
                          driver="test-driver", loser="mm wrong",
                          sen="ken_no_sen", confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        rec = bt.load_ledger()[-1]
        self.assertLess(rec["size_usd"], 2000.0)
        self.assertAlmostEqual(rec["size_usd"] + rec["unfilled_usd"],
                               rec["attempted_usd"], places=1)
        self.assertLessEqual(rec["depth_1c_usd"], 31.0)

    def test_fee_recorded_and_deducted_at_settlement(self):
        # Sports tags: fee > 0 on the receipt, netted out of settlement P&L.
        self.set_book("feemkt", 50.0, tags=("sports",))
        ns = self.book_ns(market="feemkt", price=50.0, p=0.99,
                          directive=True, confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        rec = bt.load_ledger()[-1]
        self.assertGreater(rec["fee_usd"], 0)
        self.assertEqual(rec["fee_category"], "sports")
        self.assertFalse(rec["fee_unknown"])
        # Fill-regime tag (2026-10-06): scoring panels split on this.
        self.assertEqual(rec["fill_model"], "v2-bookwalk")
        # fee = shares * 0.05 * 0.5 * 0.5; $1 directive -> 2 shares -> $0.025
        self.assertAlmostEqual(rec["fee_usd"], 0.03, places=2)
        ns = argparse.Namespace(market="feemkt", outcome="YES", pnl=None,
                                evidence="test", resolved_cdt="", note="")
        code, _ = self.quiet(bt.cmd_settle, ns)
        self.assertEqual(code, 0)
        settled = [e for e in bt.load_ledger()
                   if e.get("action") == "settle"]
        # gross win $1.00 minus $0.03 entry fee (rounded)
        self.assertAlmostEqual(settled[-1]["realized_pnl_usd"], 0.97, places=2)

    def test_entry_never_fills_above_limit(self):
        # The worker's --price is the limit: a real limit order never fills
        # above it. Thin touch at exactly the limit, fat book 1c above.
        # Without the limit filter the walk dips into 51c (VWAP 50.5c) and
        # the EV gate — evaluated at the 50c limit — overstates edge by ~1pt.
        snap = {"venue": "us", "tags": ["geopolitics"],
                "asks": [[0.50, 1.0], [0.51, 100000.0]],
                "bids": [[0.49, 100000.0]]}
        with open(self._book_stub_path) as f:
            all_snaps = json.load(f)
        all_snaps["limitmkt"] = snap
        with open(self._book_stub_path, "w") as f:
            json.dump(all_snaps, f)
        ns = self.book_ns(market="limitmkt", price=50.0, p=0.99,
                          directive=True, confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        rec = bt.load_ledger()[-1]
        # Only the 50c touch level filled; the 51c book untouched.
        self.assertLessEqual(rec["price_c"], 50.0)
        self.assertEqual(rec["price_c"], 50.0)
        self.assertAlmostEqual(rec["unfilled_usd"], 0.50, places=2)
        self.assertEqual(rec["limit_c"], 50.0)

    def test_fee_unknown_explicit_zero(self):
        self.set_book("unkmkt", 50.0, tags=("brand-new-category",))
        ns = self.book_ns(market="unkmkt", price=50.0, p=0.99,
                          directive=True, confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        rec = bt.load_ledger()[-1]
        self.assertEqual(rec["fee_usd"], 0.0)
        self.assertTrue(rec["fee_unknown"])
        self.assertEqual(rec["fee_category"], "unknown")

    def test_exit_walks_bids(self):
        self.set_book("exitmkt", 87.0, spread_c=2.0)  # bids at 85c
        ns = self.book_ns(market="exitmkt", price=87.0, p=0.99,
                          directive=True, confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        rid = bt.load_ledger()[-1]["receipt_id"]
        ns = argparse.Namespace(receipt=rid, exit_price=80.0,
                                auto_price=False, note="")
        code, _ = self.quiet(bt.cmd_exit, ns)
        self.assertEqual(code, 0)
        rec = [e for e in bt.load_ledger()
               if e.get("action") == "exit" and e["receipt_id"] == rid][0]
        self.assertEqual(rec["exit_basis"], "book-walk")
        self.assertEqual(rec["exit_price_c"], 85.0)

    def test_us_venue_fee(self):
        self.set_book("usmkt", 50.0, venue="us")
        ns = self.book_ns(market="usmkt", price=50.0, p=0.99,
                          directive=True, confirm_cents=True)
        code, _ = self.quiet(bt.cmd_book, ns)
        self.assertEqual(code, 0)
        rec = bt.load_ledger()[-1]
        self.assertEqual(rec["fill_venue"], "us")
        self.assertEqual(rec["fee_category"], "us")
        self.assertGreater(rec["fee_usd"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
