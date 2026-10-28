#!/usr/bin/env bash
# run_tests.sh — run the full Nightwatch suite against throwaway state.
#
# Every suite stages its own fixtures through testutil.py (sandboxed
# HOME, state dir, poller quotes, stub book snapshots); this runner
# additionally sandboxes HOME for the whole test process, so even a
# suite that forgot the fixture stays contained. Suites can also be
# run individually (see the README quick-start) — testutil sandboxes
# every subprocess either way. Nothing here touches live state or the
# network.
set -u
cd "$(dirname "$0")"

SANDBOX_HOME="$(mktemp -d)"
trap 'rm -rf "$SANDBOX_HOME"' EXIT
export HOME="$SANDBOX_HOME"
unset NIGHTWATCH_BOOK_STUB NIGHTWATCH_STATE_DIR

fail=0
run() {
  echo "=== $*"
  "$@" || fail=1
}

run python3 -m unittest test_book_trade
run python3 test_traps.py
run python3 test_mikiri.py
run python3 test_driver_gate.py
run python3 test_optimizer.py

if [ "$fail" -eq 0 ]; then
  echo "run_tests: all suites passed"
else
  echo "run_tests: FAILURES above" >&2
fi
exit "$fail"
