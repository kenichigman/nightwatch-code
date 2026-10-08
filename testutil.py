"""testutil.py — shared test fixture for Nightwatch tests.

Convention (AGENTS.md): tests NEVER run against the real HOME.
- Preferred: run everything via run_tests.sh, which sandboxes HOME for the
  whole test process — even a test that forgets this fixture is contained.
- Per-test: use isolated_home() below for a fresh temp HOME per test case.

A test that points at the real ledger is a spec violation, not a style issue.
"""
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

GOAL_SUBPATH = os.path.join("workspace", "goals", "10-polymarket-experiment")


@contextlib.contextmanager
def isolated_home():
    """Yield a temp HOME containing an empty goal hidden_files/ dir."""
    home = tempfile.mkdtemp(prefix="nightwatch-test-")
    os.makedirs(os.path.join(home, GOAL_SUBPATH, "hidden_files"), exist_ok=True)
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


def run_script(home, script, *args, heartbeat=True):
    """Run a goal script with HOME pointed at the isolated home.

    heartbeat=True (default) provisions a fresh price-watch heartbeat first:
    booking tests assume a live data plane unless the test says otherwise.
    Pass heartbeat=False when the test controls the heartbeat itself
    (e.g. data-health gate tests).
    """
    if heartbeat:
        setup_hook_heartbeat(home)
    env = dict(os.environ, HOME=home)
    return subprocess.run([sys.executable, script, *args],
                          env=env, capture_output=True, text=True)


def read_hidden(home, name):
    """Read a hidden_files/ artifact; .jsonl returns a list of dicts."""
    path = os.path.join(home, GOAL_SUBPATH, "hidden_files", name)
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
    """Parse PAPER.md's ## Ledger table into cell lists (12+ columns)."""
    rows = []
    path = os.path.join(home, GOAL_SUBPATH, "PAPER.md")
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s.startswith("|") and not s.startswith("|---") \
                    and not s.startswith("| Date"):
                cells = [c.strip() for c in s.strip("|").split("|")]
                if len(cells) >= 12:
                    rows.append(cells)
    return rows
