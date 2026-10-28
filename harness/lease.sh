#!/bin/bash
# lease.sh — reference-counted wake leases for a shared workstation.
#
# A lease means "a worker needs the execution host awake right now."
# Workers take a lease before touching the host and release it after.
# The last release runs the sleep decider, which may put the host back
# to sleep — never while a human is using it.
#
# The bridge: the host also runs its own overnight stay-awake check,
# which cannot see this lease registry. It honors a flag file instead.
# Every successful acquire stamps that flag (the host's own "a worker
# asked" signal); the last release clears it. Without the bridge, two
# correct stay-awake systems composed into a fault — see
# docs/execution-tier.md, section 2.
#
# Configuration is by environment; nothing site-specific lives here.
#   LEASE_DIR    controller-side lease registry (default: ./leases)
#   POWER_LOG    append-only log of lease/stamp/verdict events
#   HOST_SSH     ssh command reaching the host, e.g. "ssh exec-host"
#   WAKE_CMD     fires the wake relay; exit 0 = packet sent
#   DECIDER_CMD  runs the sleep decider on last release
#   HOST_FLAG    flag file path ON the host (default: ~/wake_need.txt)
#   STALE_SECS   leases older than this are pruned (default: 14400)
#
# Usage:
#   lease.sh acquire <worker-id> [--wake]   --wake fires WAKE_CMD if the
#                                             host is asleep, waits ~120s
#   lease.sh release <worker-id>            last release: clear + decider
#   lease.sh list | count | probe
set -euo pipefail

LEASE_DIR="${LEASE_DIR:-./leases}"
POWER_LOG="${POWER_LOG:-./power.log}"
HOST_SSH="${HOST_SSH:-ssh exec-host}"
WAKE_CMD="${WAKE_CMD:-true}"
DECIDER_CMD="${DECIDER_CMD:-true}"
HOST_FLAG="${HOST_FLAG:-~/wake_need.txt}"
STALE_SECS="${STALE_SECS:-14400}"

mkdir -p "$LEASE_DIR"
sanitize() { printf '%s' "$1" | tr -cd 'a-zA-Z0-9_.-'; }
plog() { echo "$(date '+%F %T %Z') LEASE: $*" >> "$POWER_LOG"; }

prune_stale() {
  local f age now; now=$(date +%s)
  for f in "$LEASE_DIR"/*.lease; do
    [[ -e "$f" ]] || continue
    age=$(( now - $(stat -c %Y "$f" 2>/dev/null || echo 0) ))
    if (( age > STALE_SECS )); then
      plog "pruning stale lease $(basename "$f" .lease) (age ${age}s)"
      rm -f "$f"
    fi
  done
  return 0
}

do_probe() { timeout 30 $HOST_SSH 'echo ok' >/dev/null 2>&1; }

# Stamp the host flag with today's date (the host check treats date
# content as fresh all day). Best effort: never fail a lease over it,
# never fail silently either.
stamp_flag() {
  if timeout 30 $HOST_SSH "date '+%Y-%m-%d' > $HOST_FLAG" >/dev/null 2>&1; then
    plog "flag stamped (lease bridge)"
  else
    plog "WARN: flag stamp FAILED — host check may sleep the host despite leases"
  fi
}

# Clear the stamp on last release, but only if the content is exactly a
# date (our stamp format) — a flag a human wrote is left alone.
clear_flag() {
  if timeout 30 $HOST_SSH "c=\$(cat $HOST_FLAG 2>/dev/null); case \"\$c\" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) rm -f $HOST_FLAG;; esac" >/dev/null 2>&1; then
    plog "flag cleared (last release)"
  else
    plog "WARN: flag clear FAILED — stamp may linger until date rollover"
  fi
}

cmd="${1:-}"; wid="$(sanitize "${2:-}")"
case "$cmd" in
  probe) do_probe ;;
  count) prune_stale; shopt -s nullglob; files=("$LEASE_DIR"/*.lease); echo "${#files[@]}" ;;
  list)
    prune_stale; now=$(date +%s)
    for f in "$LEASE_DIR"/*.lease; do
      [[ -e "$f" ]] || continue
      echo "$(basename "$f" .lease) age=$(( now - $(stat -c %Y "$f") ))s"
    done ;;
  acquire)
    [[ -n "$wid" ]] || { echo "acquire needs <worker-id>" >&2; exit 2; }
    if ! do_probe; then
      if [[ "${3:-}" == "--wake" ]]; then
        plog "acquire($wid): host unreachable, firing wake"
        if ! $WAKE_CMD >/dev/null 2>&1; then
          plog "acquire($wid): wake request failed"; exit 3
        fi
        waited=0
        while (( waited < 120 )); do sleep 10; (( waited += 10 )) || true; do_probe && break; done
        do_probe || { plog "acquire($wid): still unreachable after wake"; exit 3; }
        plog "acquire($wid): host awake after wake (${waited}s)"
      else
        exit 3
      fi
    fi
    touch "$LEASE_DIR/$wid.lease"
    plog "acquire($wid): lease held"
    stamp_flag || true
    echo "acquired $wid" ;;
  release)
    [[ -n "$wid" ]] || { echo "release needs <worker-id>" >&2; exit 2; }
    rm -f "$LEASE_DIR/$wid.lease"
    plog "release($wid): lease dropped"
    n=$("$0" count)
    if (( n == 0 )); then
      clear_flag || true
      plog "release($wid): last lease, running sleep decider"
      $DECIDER_CMD || true
    else
      plog "release($wid): $n lease(s) remain, no decider run"
    fi
    echo "released $wid ($n leases remain)" ;;
  *) echo "usage: $0 {acquire <id> [--wake]|release <id>|list|count|probe}" >&2; exit 2 ;;
esac
