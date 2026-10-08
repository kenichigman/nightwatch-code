#!/usr/bin/env python3
"""Jev L4 calibration grader: predicted confidence vs graded accuracy.

Soak files carry per-item "confs" (parsed [conf:X.XX] tags). After hand
grading, add "bad_lines": [i, ...] (0-indexed output lines with factual
contradictions; omitted = all clean). This script bins confidence and
reports accuracy per bin so the escalation threshold is set from data.

Usage: local_calibrate.py hidden_files/local_soak_*.json
"""
import json
import re
import sys

BINS = [(0.50, 0.70), (0.70, 0.85), (0.85, 0.95), (0.95, 1.01)]


def main() -> int:
    bins = {b: [] for b in BINS}
    n_items = n_lines = 0
    for path in sys.argv[1:]:
        d = json.load(open(path))
        for it in d["items"]:
            if "confs" not in it or not it["confs"]:
                continue
            n_items += 1
            bad = set(it.get("bad_lines", []))
            if "claims" in it:
                # span-contract format: confs align to claims by index;
                # bad_lines indexes claims, not text lines.
                units = [(c, cf, k)
                         for k, (c, cf) in enumerate(zip(it["claims"],
                                                         it["confs"]))]
            else:
                # legacy text format: confs parsed from output lines.
                units = []
                for i, ln in enumerate(it["output"].splitlines()):
                    m = re.search(r"\[conf:(0\.\d{2}|1\.00)\]", ln)
                    if m:
                        units.append((ln, float(m.group(1)), i))
            for _, conf, idx in units:
                ok = idx not in bad
                for b in BINS:
                    if b[0] <= conf < b[1]:
                        bins[b].append(ok)
                        break
                n_lines += 1
    print(f"items={n_items} graded_lines={n_lines}")
    print(f"{'bin':<14}{'n':>5}{'acc':>8}{'mean_conf':>10}")
    for b in BINS:
        v = bins[b]
        if not v:
            print(f"{b[0]:.2f}-{b[1]:.2f}     {'-':>5}{'':>8}{'':>10}")
            continue
        acc = sum(v) / len(v)
        print(f"{b[0]:.2f}-{b[1]:.2f}  {len(v):>5}{acc:>8.2f}")
    print("\nSet the escalation threshold at the bin edge below which "
          "accuracy falls under the bar (bar: 0.95 for advisory use).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
