#!/usr/bin/env python3
"""Circuit breaker for the local inference tier.

Probabilistic-collapse protection, complementing the deterministic
tripwires (canary set, cryptographic pins). Evaluates the trailing
local_tier_heartbeat.jsonl log on every pre-flight and trips when the
LLM path shows:

 - hard cliff: 2 consecutive llm_transport_failed (a down server is a
 binary infrastructure state; a third 19s cycle proves nothing), or
 3 consecutive faults of any class (gate_refused / llm_bad_output /
 llm_transport_failed);
 - slow rot: faults in >= 50% of the trailing 10 LLM attempts
 (minimum 5 attempts before the density rule can fire).

On trip, writes hidden_files/circuit.trip and appends the incident to
hidden_files/circuit_history.jsonl (append-only incident record). The
tier refuses all invocations until the trip file is manually reviewed
and cleared — OR until the half-open probe (below) verifies recovery
itself.

Half-open state (the operator's directive): a latched trip is a
blind spot after recovery — the Ollama outage was fixed
but the breaker kept refusing on a stale timestamp for 9
cycles because no new heartbeat entries can accrue while the tier
refuses. So before the pre-flight refuses on circuit.trip, it calls
half_open_probe: if the trip is older than HALF_OPEN_INTERVAL since the
last probe, the breaker re-probes the tier directly (two-signal:
/api/tags then a minimal /api/generate through the tunnel proxy). Probe
success auto-clears the trip and records a half_open_clear incident;
probe failure leaves the trip in place and records the attempt in
hidden_files/circuit.halfopen (NOT in history — no spam). The probe
never writes to the heartbeat log, so it cannot manufacture evidence,
and it never touches canary.trip / pin.trip (deterministic tripwires
stay manual-clear only).

Vocabulary stratification:
 faults: llm_transport_failed, gate_refused, llm_bad_output
 benign: llm_ok (resets consecutive counters); gpu_busy_yield,
 guard_unreachable_yield, skipped_no_input (neutral: neither
 increment nor reset; non-attempts never dilute the density
 denominator, and the designed CPU fallback is never
 punished for working)
 excluded: any entry whose detail names canary_trip / pin_trip /
 circuit_trip (anti-feedback: trip-driven refusals must not
 stack phantom breaker trips on top of real ones).

Post-clear re-trip guard: evaluate ignores heartbeat entries at or
before the newest entry timestamp recorded by the most recent trip
incident. Without this, clearing the trip file would re-trip on the
same evidence on the very next pre-flight (no new entries can accrue
while the tier refuses), bricking the tier permanently. New faults
after a clear trip on genuinely new evidence, as intended.

Missing/unreadable heartbeat log -> fail-open (no trip). The breaker
measures LLM health, not disk integrity; a broken logging layer is the
system health-check's diagnostic context, not this breaker's.
"""

import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.environ.get("NIGHTWATCH_HOME", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG = f"{HERE}/hidden_files/local_tier_heartbeat.jsonl"
CIRCUIT_TRIP = f"{HERE}/hidden_files/circuit.trip"
HISTORY = f"{HERE}/hidden_files/circuit_history.jsonl"
HALFOPEN_STATE = f"{HERE}/hidden_files/circuit.halfopen"

TRANSPORT_FAST_TRIP = 2       # consecutive llm_transport_failed
QUALITY_CONSECUTIVE_TRIP = 3  # consecutive faults of any class
DENSITY_WINDOW = 10           # trailing eligible LLM attempts
DENSITY_MIN_ATTEMPTS = 5      # min sample before density can fire
DENSITY_FAULT_FRACTION = 0.5
TAIL_LINES = 500
HALF_OPEN_INTERVAL = 1800     # seconds between half-open re-probes
GDESK = os.environ.get("GDESK_HOST", "localhost")  # local Ollama endpoint; override via GDESK_HOST
OLLAMA_PORT = 11434

FAULT_PATHS = {"llm_transport_failed", "gate_refused", "llm_bad_output"}
TRIP_MARKERS = ("canary_trip", "pin_trip", "circuit_trip")


def _is_trip_refusal(detail: str) -> bool:
    return any(m in (detail or "") for m in TRIP_MARKERS)


def _last_trip_watermark(history_path: str = HISTORY) -> str:
    """Newest heartbeat entry ts consumed by the most recent trip incident.

 Returns "" when no incident is recorded (fail-open: evaluate everything).
 Skips non-trip records (e.g. half_open_clear) so an auto-clear never
 moves the watermark — post-clear evaluation must ignore the same
 evidence the trip already consumed, exactly as after a manual clear.
 Records predating the kind field are treated as trips.
 """
    try:
        with open(history_path) as f:
            lines = f.readlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("kind", "trip") != "trip":
            continue
        ts = rec.get("newest_entry_ts") or ""
        if ts:
            return ts
    return ""


def _record_incident(reason: str, newest_entry_ts: str,
                     history_path: str = HISTORY,
                     kind: str = "trip") -> None:
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "kind": kind,
        "reason": reason,
        "newest_entry_ts": newest_entry_ts,
    }
    with open(history_path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def evaluate(log_path: str = LOG,
             history_path: str = HISTORY) -> tuple:
    """Return (tripped: bool, reason: str). Never raises on I/O problems."""
    try:
        with open(log_path) as f:
            lines = f.readlines()[-TAIL_LINES:]
    except OSError:
        return False, "no heartbeat log (fail-open)"
    watermark = _last_trip_watermark(history_path)
    consec_all = 0
    consec_transport = 0
    window: list = []          # trailing eligible attempts, oldest-first
    newest_ts = ""             # newest eligible entry ts seen this pass
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        path = rec.get("path")
        detail = rec.get("detail") or ""
        if path not in FAULT_PATHS and path != "llm_ok":
            continue                       # benign non-attempt: neutral
        if _is_trip_refusal(detail):
            continue                       # anti-feedback
        ts = rec.get("ts") or ""
        if watermark and ts and ts <= watermark:
            continue                       # already consumed by a past trip
        if ts and ts > newest_ts:
            newest_ts = ts
        if path == "llm_ok":
            consec_all = 0
            consec_transport = 0
            window.append(False)
            continue
        consec_all += 1                    # fault of some class
        if path == "llm_transport_failed":
            consec_transport += 1
        else:
            consec_transport = 0
        window.append(True)
        if consec_transport >= TRANSPORT_FAST_TRIP:
            return True, (f"mechanism=consecutive_transport "
                          f"faults={consec_transport}")
        if consec_all >= QUALITY_CONSECUTIVE_TRIP:
            return True, f"mechanism=consecutive faults={consec_all}"
    window = window[-DENSITY_WINDOW:]
    if len(window) >= DENSITY_MIN_ATTEMPTS:
        faults = sum(window)
        if faults / len(window) >= DENSITY_FAULT_FRACTION:
            return True, f"mechanism=density faults={faults}/{len(window)}"
    return False, "ok"


def check(log_path: str = LOG, trip_path: str = CIRCUIT_TRIP,
          history_path: str = HISTORY) -> tuple:
    """Evaluate and actuate: write the trip file + incident on trip."""
    tripped, reason = evaluate(log_path, history_path)
    if not tripped:
        return False, reason
    newest_ts = ""
    try:
        with open(log_path) as f:
            for line in f.readlines()[-TAIL_LINES:]:
                try:
                    ts = json.loads(line).get("ts") or ""
                except ValueError:
                    continue
                if ts > newest_ts:
                    newest_ts = ts
    except OSError:
        pass
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        with open(trip_path, "w") as f:
            f.write(f"{stamp} circuit_trip: {reason}\n")
        _record_incident(reason, newest_ts, history_path)
    except OSError as exc:
        return False, f"trip write failed: {exc}"
    return True, reason


def _tunnel_proxy() -> str:
    https_proxy = os.environ.get("HTTPS_PROXY", "")
    if not https_proxy:
        raise RuntimeError("HTTPS_PROXY not set; cannot derive tunnel proxy")
    return f"{https_proxy.rsplit(':', 1)[0]}:3130"


def _probe_tier(timeout: int = 30) -> tuple:
    """Two-signal liveness probe: /api/tags, then a minimal /api/generate.

 Returns (ok, detail). Never raises; never writes to the heartbeat log.
 Same route as ollama_local.py (tunnel proxy port 3130, not direct).
 """
    try:
        proxy = _tunnel_proxy()
        os.environ["https_proxy"] = proxy
        os.environ["http_proxy"] = proxy
        req = urllib.request.Request(f"http://{GDESK}:{OLLAMA_PORT}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False, f"tags http={resp.status}"
        payload = {"model": "qwen2.5:14b", "prompt": "ping", "stream": False,
                   "keep_alive": "2h",
                   "options": {"temperature": 0.0, "num_predict": 1}}
        req = urllib.request.Request(
            f"http://{GDESK}:{OLLAMA_PORT}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.load(resp)
        if "response" in body:
            return True, "tags=200 generate=ok"
        return False, "generate: no response field"
    except Exception as exc:  # noqa: BLE001 - fail-closed, detail only
        return False, f"{type(exc).__name__}: {exc}"


def _read_halfopen_state(state_path: str = HALFOPEN_STATE) -> dict:
    try:
        with open(state_path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def half_open_probe(trip_path: str = CIRCUIT_TRIP,
                    history_path: str = HISTORY,
                    state_path: str = HALFOPEN_STATE,
                    now: float | None = None) -> tuple:
    """Re-probe a latched trip on schedule; auto-clear on recovery.

 Returns (acted, detail). Only ever touches the circuit trip file —
 canary.trip / pin.trip are never probed or cleared here.
 Fail-closed: any probe or I/O failure leaves the trip in place.
 """
    if now is None:
        now = time.time()
    try:
        trip_mtime = os.path.getmtime(trip_path)
    except OSError:
        return False, "no trip file"
    state = _read_halfopen_state(state_path)
    last_probe = state.get("last_probe_ts") or trip_mtime
    if now - last_probe < HALF_OPEN_INTERVAL:
        return False, "probe not due"
    ok, detail = _probe_tier()
    state_rec = {"last_probe_ts": now, "last_probe_ok": ok, "detail": detail}
    if ok:
        try:
            os.remove(trip_path)
        except OSError as exc:
            return False, f"clear failed: {exc}"
        watermark = _last_trip_watermark(history_path)
        try:
            _record_incident(f"half_open_clear: {detail}", watermark,
                             history_path, kind="half_open_clear")
        except OSError as exc:
            detail = f"{detail} (history write failed: {exc})"
        try:
            with open(state_path, "w") as f:
                json.dump(state_rec, f)
        except OSError:
            pass
        return True, f"trip auto-cleared: {detail}"
    try:
        with open(state_path, "w") as f:
            json.dump(state_rec, f)
    except OSError:
        pass
    return False, f"probe failed, trip stays: {detail}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", default=LOG)
    ap.add_argument("--trip-file", default=CIRCUIT_TRIP)
    ap.add_argument("--history", default=HISTORY)
    ap.add_argument("--no-actuate", action="store_true",
                    help="evaluate only; do not write trip file or history")
    args = ap.parse_args()
    if args.no_actuate:
        tripped, reason = evaluate(args.log, args.history)
    else:
        tripped, reason = check(args.log, args.trip_file, args.history)
    print(f"circuit_breaker: tripped={tripped} {reason}")
    return 2 if tripped else 0


if __name__ == "__main__":
    raise SystemExit(main())
