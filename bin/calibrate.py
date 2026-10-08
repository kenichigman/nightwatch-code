#!/usr/bin/env python3
"""bin/calibrate.py — offline per-desk probability calibration (ML, read-only).

Gabe 2026-09-26: "use ML if you think best." The honest ML win in this stack is
calibration: map each desk's reported p to its empirical hit rate, so the EV
gate prices reality instead of self-assessment.

Reads brier_shadow.json scored rows (p, outcome per desk — X and directive
rows never enter, per policy). Reports per-desk reliability. Fits Platt scaling
(1D logistic regression, Newton/IRLS, hand-rolled — no sklearn on this box)
and isotonic regression (PAVA), but ONLY when a desk has >=15 scored rows
(the SPEC.md propose-recalibrate threshold). Model selection by 5-fold CV
Brier: raw p vs Platt vs isotonic.

Output: hidden_files/calibration_maps.json — READ-ONLY. NOTHING consumes it.
Doctrine gate (manual-first, Gabe-approved): the maps stay UNWIRED from
booking until the first propose badge is hand-worked by K3N1 and a golden eval
set exists. book_trade.py's desk_calibration() keeps reading raw scored rows.
"""
import bisect
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.expanduser("~/workspace/goals/10-polymarket-experiment")
SHADOW = os.path.join(ROOT, "hidden_files", "brier_shadow.json")
MAPS = os.path.join(ROOT, "hidden_files", "calibration_maps.json")
CDT = timezone(timedelta(hours=-5))
MIN_N = 15  # SPEC.md propose-recalibrate threshold


def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def fit_platt(xs, ys):
    """1D logistic regression y ~ sigmoid(a*x + b) via Newton/IRLS."""
    a, b = 0.0, 0.0
    base = sum(ys) / len(ys)
    if 0 < base < 1:
        b = math.log(base / (1 - base))
    for _ in range(25):
        ga = gb = haa = hab = hbb = 0.0
        for x, y in zip(xs, ys):
            mu = sigmoid(a * x + b)
            w = max(mu * (1 - mu), 1e-9)
            r = y - mu
            ga += r * x
            gb += r
            haa += w * x * x
            hab += w * x
            hbb += w
        haa += 1e-6
        hbb += 1e-6
        det = haa * hbb - hab * hab
        if abs(det) < 1e-12:
            break
        da = (ga * hbb - gb * hab) / det
        db = (gb * haa - ga * hab) / det
        a += da
        b += db
        if abs(da) + abs(db) < 1e-8:
            break
    return a, b


def fit_isotonic(xs, ys):
    """PAVA isotonic regression on (x, y) sorted by x. Returns knot lists."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    sx = [xs[i] for i in order]
    sy = [ys[i] for i in order]
    # pools: [sum_y, count, x_lo, x_hi]
    pools = [[y, 1, x, x] for x, y in zip(sx, sy)]
    i = 0
    while i < len(pools) - 1:
        if pools[i][0] / pools[i][1] <= pools[i + 1][0] / pools[i + 1][1] + 1e-12:
            i += 1
        else:
            p0, p1 = pools[i], pools[i + 1]
            pools[i] = [p0[0] + p1[0], p0[1] + p1[1], p0[2], p1[3]]
            del pools[i + 1]
            if i > 0:
                i -= 1
    knots_x = [p[3] for p in pools]          # right edge of each pool
    knots_v = [p[0] / p[1] for p in pools]   # pool mean
    return knots_x, knots_v


def apply_isotonic(knots_x, knots_v, x):
    i = bisect.bisect_left(knots_x, x)
    return knots_v[min(i, len(knots_v) - 1)]


def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ps)


def cv_brier(xs, ys, method, k=5):
    n = len(xs)
    folds = [[] for _ in range(k)]
    for i in range(n):
        folds[i % k].append(i)
    tot, cnt = 0.0, 0
    for f in range(k):
        te = folds[f]
        tr = [i for i in range(n) if i not in set(te)]
        if not tr or not te:
            continue
        tx, ty = [xs[i] for i in tr], [ys[i] for i in tr]
        ex, ey = [xs[i] for i in te], [ys[i] for i in te]
        if method == "raw":
            pred = ex
        elif method == "platt":
            a, bb = fit_platt(tx, ty)
            pred = [sigmoid(a * x + bb) for x in ex]
        else:
            kx, kv = fit_isotonic(tx, ty)
            pred = [apply_isotonic(kx, kv, x) for x in ex]
        tot += sum((p - y) ** 2 for p, y in zip(pred, ey))
        cnt += len(ey)
    return tot / cnt if cnt else float("inf")


def reliability(xs, ys, bins=5):
    out = []
    for bi in range(bins):
        lo, hi = bi / bins, (bi + 1) / bins
        sel = [y for x, y in zip(xs, ys) if (lo <= x < hi) or (bi == bins - 1 and x == hi)]
        if sel:
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(sel),
                        "mean_p": round(sum(x for x, y in zip(xs, ys)
                                            if (lo <= x < hi) or (bi == bins - 1 and x == hi)) / len(sel), 3),
                        "hit_rate": round(sum(sel) / len(sel), 3)})
    return out


def main():
    try:
        with open(SHADOW) as f:
            scored = json.load(f).get("scored") or []
    except Exception as e:
        print(f"calibrate: cannot read brier_shadow.json ({e})")
        return 1
    by_desk = {}
    for r in scored:
        by_desk.setdefault(r.get("desk", "?"), []).append(r)

    maps = {}
    now = datetime.now(CDT).strftime("%Y-%m-%d %H:%M %Z")
    print(f"calibrate: {len(scored)} scored rows across {len(by_desk)} desks")
    for desk in sorted(by_desk):
        rows = by_desk[desk]
        xs = [float(r["p"]) for r in rows]
        ys = [int(r["outcome"]) for r in rows]
        n = len(xs)
        base = sum(ys) / n
        raw = brier(xs, ys)
        print(f"\n[{desk}] n={n} mean_p={sum(xs)/n:.3f} base_rate={base:.3f} brier={raw:.4f}")
        for b in reliability(xs, ys):
            print(f"    bin {b['bin']}: n={b['n']} mean_p={b['mean_p']} hit={b['hit_rate']}")
        if n < MIN_N:
            print(f"    -> insufficient data for mapping (need >={MIN_N} scored)")
            continue
        if base in (0.0, 1.0):
            print("    -> degenerate base rate; no fit")
            continue
        cv_raw = cv_brier(xs, ys, "raw")
        cv_platt = cv_brier(xs, ys, "platt")
        cv_iso = cv_brier(xs, ys, "isotonic")
        print(f"    CV brier: raw={cv_raw:.4f} platt={cv_platt:.4f} isotonic={cv_iso:.4f}")
        best = min(("raw", cv_raw), ("platt", cv_platt), ("isotonic", cv_iso),
                   key=lambda t: t[1])
        if best[0] == "raw":
            print("    -> no mapping beats raw p; no map written")
            continue
        if best[0] == "platt":
            a, bb = fit_platt(xs, ys)
            params = {"a": round(a, 4), "b": round(bb, 4)}
        else:
            kx, kv = fit_isotonic(xs, ys)
            params = {"knots_x": [round(v, 4) for v in kx],
                      "knots_v": [round(v, 4) for v in kv]}
        maps[desk] = {"method": best[0], "params": params, "n": n,
                      "cv_brier_raw": round(cv_raw, 4),
                      "cv_brier": round(best[1], 4),
                      "fitted_cdt": now,
                      "status": "UNWIRED — manual-first doctrine: hand-work the "
                                "first propose badge before anything consumes this"}
        print(f"    -> map written ({best[0]}), UNWIRED per doctrine")
    with open(MAPS, "w") as f:
        json.dump({"_comment": "Per-desk p-calibration maps. READ-ONLY: nothing consumes "
                              "this file until the manual-first doctrine gate clears "
                              "(first propose badge hand-worked, golden eval set).",
                   "maps": maps}, f, indent=1)
    print(f"\ncalibrate: wrote {MAPS} ({len(maps)} maps, all unwired)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
