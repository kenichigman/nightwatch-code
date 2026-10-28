"""testutil.py — shared test fixture for Nightwatch tests.

Convention: tests NEVER run against the real HOME or state dir.
- Preferred: run everything via run_tests.sh, which sandboxes HOME for the
 whole test process — even a test that forgets this fixture is contained.
- Per-test: use isolated_home below for a fresh temp HOME per test case.

run_script wires each subprocess to the sandbox on every axis the code
under test can read:
- HOME — the HOME-relative state (bin/traps.py, the hook files).
- NIGHTWATCH_STATE_DIR — book_trade.py's state dir (its production
 default is beside the script; the harness overrides it, never the
 reverse).
- NIGHTWATCH_BOOK_STUB — the honest-fill book snapshot. Entries walk a
 depth snapshot and fail closed without one, so the harness plants
 stub books (plant_book) instead of letting a test reach a live venue.

A test that points at the real ledger is a spec violation, not a style issue.
"""
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

GOAL_SUBPATH = "nightwatch"


@contextlib.contextmanager
def isolated_home():
    """Yield a temp HOME containing an empty goal state/ dir."""
    home = tempfile.mkdtemp(prefix="nightwatch-test-")
    os.makedirs(os.path.join(home, GOAL_SUBPATH, "state"), exist_ok=True)
    try:
        yield home
    finally:
        shutil.rmtree(home, ignore_errors=True)


def setup_hook_heartbeat(home, age_s=0, fetch_ok=1, fetch_fail=0):
    """Write a price-watch heartbeat into the sandboxed HOME.

 The book_trade.py data-health gate (Phase 1.1) fails closed without a
 fresh heartbeat, so booking tests must prove the sensor is alive.
 age_s backdates last_tick (stale-heartbeat tests); fetch_ok=0 with
 fetch_fail>0 simulates a transport-dark tick.
 """
    from datetime import datetime, timedelta, timezone
    d = os.path.join(home, "hooks", "state")
    os.makedirs(d, exist_ok=True)
    tick = (datetime.now(timezone.utc) - timedelta(seconds=age_s))
    with open(os.path.join(d, "nightwatch-status.json"), "w") as f:
        json.dump({"last_tick": tick.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "markets_watched": 1, "last_alert": "",
                   "fetch_ok": fetch_ok, "fetch_fail": fetch_fail}, f)


def stub_path(home):
    """The sandbox's honest-fill book-stub file (see plant_book)."""
    return os.path.join(home, "book_stub.json")


def _merge_json(path, updates):
    doc = {}
    if os.path.exists(path):
        with open(path) as f:
            doc = json.load(f)
    doc.update(updates)
    with open(path, "w") as f:
        json.dump(doc, f)
    return doc


def plant_book(home, market, price_c, venue="com", tags=("geopolitics",),
               depth_usd=1e9, spread_c=1.0):
    """Plant a deep two-sided stub book for market at price_c.

 Mirrors test_book_trade.py's set_book: the ask touch sits exactly at
 the test's limit price, so fills execute at the stated price by
 construction, with depth that never binds.
 """
    p = price_c / 100.0
    bid_p = max(p - spread_c / 100.0, 0.01)
    snap = {"venue": venue, "tags": list(tags),
            "asks": [[p, depth_usd / p]],
            "bids": [[bid_p, depth_usd / bid_p]]}
    _merge_json(stub_path(home), {market: snap})


def plant_quote(home, market, price_c):
    """Plant a poller quote for market at price_c.

 Merges the market into the sandbox watchlist (state/watchlist.json)
 and the hook price cache (~/hooks/state/nightwatch-prices.json) that
 book_trade.py's price-unit gate reads, so the gate sees a direct
 quote match and the gate UNDER TEST is what decides the booking.
 """
    state = os.path.join(home, GOAL_SUBPATH, "state")
    os.makedirs(state, exist_ok=True)
    wl_path = os.path.join(state, "watchlist.json")
    wl = {}
    if os.path.exists(wl_path):
        with open(wl_path) as f:
            wl = json.load(f)
    wl.setdefault("markets", {})[market] = {"slug": market}
    with open(wl_path, "w") as f:
        json.dump(wl, f)
    hooks = os.path.join(home, "hooks", "state")
    os.makedirs(hooks, exist_ok=True)
    _merge_json(os.path.join(hooks, "nightwatch-prices.json"),
                {market: {"px": price_c / 100.0}})


def run_script(home, script, *args, heartbeat=True):
    """Run a goal script wired to the isolated home (see module docstring).

 heartbeat=True (default) provisions a fresh price-watch heartbeat first:
 booking tests assume a live data plane unless the test says otherwise.
 Pass heartbeat=False when the test controls the heartbeat itself
 (e.g. data-health gate tests).
 """
    if heartbeat:
        setup_hook_heartbeat(home)
    if not os.path.exists(stub_path(home)):
        with open(stub_path(home), "w") as f:
            json.dump({}, f)
    env = dict(os.environ, HOME=home,
               NIGHTWATCH_STATE_DIR=os.path.join(home, GOAL_SUBPATH, "state"),
               NIGHTWATCH_BOOK_STUB=stub_path(home))
    return subprocess.run([sys.executable, script, *args],
                          env=env, capture_output=True, text=True)


def read_hidden(home, name):
    """Read a state/ artifact; .jsonl returns a list of dicts."""
    path = os.path.join(home, GOAL_SUBPATH, "state", name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        content = f.read().strip()
    if not content:
        return [] if name.endswith(".jsonl") else ""
    if name.endswith(".jsonl"):
        return [json.loads(line) for line in content.split("\n") if line.strip()]
    return content


def paper_rows(home):
    """Parse paper_ledger.md's ## Ledger table into cell lists (12+ columns)."""
    rows = []
    path = os.path.join(home, GOAL_SUBPATH, "paper_ledger.md")
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s.startswith("|") and not s.startswith("|---") \
                    and not s.startswith("| Date"):
                cells = [c.strip() for c in s.strip("|").split("|")]
                if len(cells) >= 12:
                    rows.append(cells)
    return rows
