#!/usr/bin/env python3
"""Statistics for analysis decisions. Standard library only (Python 3.8+).

Commands:
  wilson     --k K --n N [--conf 0.95] [--two-sided]
  verdict    --k K --n N --threshold T [--conf 0.95]
  min-n      --threshold T [--expected-rate R] [--conf 0.95]
  stability  --threshold T (--rows "label:n:k,..." | --csv FILE) [--min-n 30]
  compare    --k1 K1 --n1 N1 --k2 K2 --n2 N2 [--conf 0.95]
  --selftest

Add --json for machine-readable output.
"""
import argparse
import csv
import json
import math
import sys
from statistics import NormalDist

PASS, FAIL, INSUFFICIENT = "PASS", "FAIL", "INSUFFICIENT"


def z_value(conf, two_sided):
    tail = (1 - conf) / 2 if two_sided else (1 - conf)
    return NormalDist().inv_cdf(1 - tail)


def wilson(k, n, conf=0.95, two_sided=False):
    """Wilson score interval. One-sided by default: the upper bound is what decisions use."""
    if n < 0 or k < 0 or k > n:
        raise ValueError("need 0 <= k <= n")
    if n == 0:
        return {"k": k, "n": n, "point": None, "lower": 0.0, "upper": 1.0}
    z = z_value(conf, two_sided)
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {
        "k": k,
        "n": n,
        "point": p,
        "lower": max(0.0, (center - margin) / denom),
        "upper": min(1.0, (center + margin) / denom),
    }


def verdict(k, n, threshold, conf=0.95):
    w = wilson(k, n, conf)
    if n == 0:
        result, why = INSUFFICIENT, "no cases"
    elif w["point"] > threshold:
        result, why = FAIL, "observed rate is above the threshold"
    elif w["upper"] <= threshold:
        result, why = PASS, "upper bound is within the threshold"
    else:
        result, why = INSUFFICIENT, "observed rate is fine, but the upper bound exceeds the threshold"
    return dict(w, threshold=threshold, verdict=result, reason=why)


def min_n(threshold, expected_rate=0.0, conf=0.95, limit=10_000_000):
    """Smallest n such that, at the expected error rate (k = rate * n, not rounded), the upper bound is <= threshold."""
    if not 0 <= expected_rate < threshold:
        raise ValueError("need 0 <= expected-rate < threshold")
    lo, hi = 1, 1
    while wilson(expected_rate * hi, hi, conf)["upper"] > threshold:
        hi *= 2
        if hi > limit:
            return None
    while lo < hi:
        mid = (lo + hi) // 2
        if wilson(expected_rate * mid, mid, conf)["upper"] <= threshold:
            hi = mid
        else:
            lo = mid + 1
    return lo


def stability(rows, threshold, conf=0.95, min_period_n=30):
    """Per-period check. A period is UNSTABLE when even its lower bound is above the threshold
    (the period is bad with confidence); WATCH when only the observed rate is above it (could be
    noise of a small month — look at it, do not conclude)."""
    periods = []
    for label, n, k in rows:
        v = verdict(k, n, threshold, conf)
        if n < min_period_n:
            flag = "too few cases"
        elif v["lower"] > threshold:
            flag = "UNSTABLE"
        elif v["point"] > threshold:
            flag = "watch"
        else:
            flag = ""
        periods.append(dict(v, label=label, flag=flag))
    total_k = sum(r[2] for r in rows)
    total_n = sum(r[1] for r in rows)
    overall = verdict(total_k, total_n, threshold, conf)
    bad = [p["label"] for p in periods if p["flag"] == "UNSTABLE"]
    watch = [p["label"] for p in periods if p["flag"] == "watch"]
    return {"periods": periods, "overall": overall, "unstable_periods": bad,
            "watch_periods": watch, "stable": not bad}


def compare(k1, n1, k2, n2, conf=0.95):
    """Two-proportion z-test (pooled) and Wald interval for p2 - p1."""
    if min(n1, n2) == 0:
        raise ValueError("n1 and n2 must be > 0")
    p1, p2 = k1 / n1, k2 / n2
    pooled = (k1 + k2) / (n1 + n2)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - NormalDist().cdf(abs(z)))
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    zc = z_value(conf, two_sided=True)
    diff = p2 - p1
    return {"p1": p1, "p2": p2, "diff": diff, "lower": diff - zc * se, "upper": diff + zc * se,
            "z": z, "p_value": p_value,
            "significant": not (diff - zc * se <= 0 <= diff + zc * se)}


def parse_rows(text):
    rows = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        label, n, k = item.rsplit(":", 2)
        rows.append((label, int(n), int(k)))
    return rows


def read_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = {c.lower(): c for c in reader.fieldnames or []}
        missing = {"period", "n", "k"} - set(cols)
        if missing:
            raise ValueError("CSV needs columns period,n,k; missing: " + ", ".join(sorted(missing)))
        return [(r[cols["period"]], int(r[cols["n"]]), int(r[cols["k"]])) for r in reader]


def pct(x):
    return "n/a" if x is None else f"{100 * x:.2f}%"


def print_human(cmd, res):
    if cmd == "wilson":
        print(f"k={res['k']} n={res['n']} point={pct(res['point'])} "
              f"lower={pct(res['lower'])} upper={pct(res['upper'])}")
    elif cmd == "verdict":
        print(f"{res['verdict']}: point={pct(res['point'])} upper={pct(res['upper'])} "
              f"threshold={pct(res['threshold'])} (k={res['k']}, n={res['n']}) — {res['reason']}")
    elif cmd == "min-n":
        print(f"min n = {res['min_n']} (threshold {pct(res['threshold'])}, "
              f"expected rate {pct(res['expected_rate'])})")
    elif cmd == "stability":
        for p in res["periods"]:
            print(f"{p['label']}: n={p['n']} k={p['k']} point={pct(p['point'])} "
                  f"lower={pct(p['lower'])} upper={pct(p['upper'])} {p['flag']}".rstrip())
        o = res["overall"]
        print(f"OVERALL {o['verdict']}: n={o['n']} k={o['k']} point={pct(o['point'])} "
              f"upper={pct(o['upper'])}")
        print("STABLE" if res["stable"] else "UNSTABLE: " + ", ".join(res["unstable_periods"]))
        if res["watch_periods"]:
            print("WATCH (above threshold, not significant): " + ", ".join(res["watch_periods"]))
    elif cmd == "compare":
        print(f"p1={pct(res['p1'])} p2={pct(res['p2'])} diff={pct(res['diff'])} "
              f"CI=[{pct(res['lower'])}, {pct(res['upper'])}] p-value={res['p_value']:.4f} "
              f"{'SIGNIFICANT' if res['significant'] else 'NOT SIGNIFICANT'}")


def selftest():
    def close(a, b, tol=5e-5):
        return abs(a - b) <= tol

    checks = [
        ("wilson 0/133 upper", close(wilson(0, 133)["upper"], 0.0199, 1e-4)),
        ("wilson 10/1000 upper", close(wilson(10, 1000)["upper"], 0.0167, 1e-4)),
        ("wilson 40/1000 upper", close(wilson(40, 1000)["upper"], 0.0515, 1e-4)),
        ("verdict 10/1000 PASS", verdict(10, 1000, 0.02)["verdict"] == PASS),
        ("verdict 5/500 INSUFFICIENT", verdict(5, 500, 0.02)["verdict"] == INSUFFICIENT),
        ("verdict 40/1000 FAIL", verdict(40, 1000, 0.02)["verdict"] == FAIL),
        ("verdict 0/0 INSUFFICIENT", verdict(0, 0, 0.02)["verdict"] == INSUFFICIENT),
        ("min-n zero errors = 133", min_n(0.02) == 133),
        ("stability flags bad month",
         stability([("a", 500, 2), ("b", 500, 25)], 0.02)["unstable_periods"] == ["b"]),
        ("stability: small noisy month is only 'watch'",
         stability([("a", 500, 2), ("b", 110, 3)], 0.02)["watch_periods"] == ["b"]
         and stability([("a", 500, 2), ("b", 110, 3)], 0.02)["stable"]),
        ("compare significant", compare(60, 1000, 20, 1000)["significant"]),
        ("compare not significant", not compare(20, 1000, 22, 1000)["significant"]),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("ok   " if ok else "FAIL ") + name)
    return 1 if failed else 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--conf", type=float, default=0.95)
        p.add_argument("--json", action="store_true")

    p = sub.add_parser("wilson"); p.add_argument("--k", type=int, required=True)
    p.add_argument("--n", type=int, required=True); p.add_argument("--two-sided", action="store_true"); common(p)
    p = sub.add_parser("verdict"); p.add_argument("--k", type=int, required=True)
    p.add_argument("--n", type=int, required=True); p.add_argument("--threshold", type=float, required=True); common(p)
    p = sub.add_parser("min-n"); p.add_argument("--threshold", type=float, required=True)
    p.add_argument("--expected-rate", type=float, default=0.0); common(p)
    p = sub.add_parser("stability"); p.add_argument("--threshold", type=float, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--rows"); g.add_argument("--csv")
    p.add_argument("--min-n", type=int, default=30); common(p)
    p = sub.add_parser("compare")
    for name in ("--k1", "--n1", "--k2", "--n2"):
        p.add_argument(name, type=int, required=True)
    common(p)

    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.cmd:
        ap.print_help()
        return 2
    try:
        if args.cmd == "wilson":
            res = wilson(args.k, args.n, args.conf, args.two_sided)
        elif args.cmd == "verdict":
            res = verdict(args.k, args.n, args.threshold, args.conf)
        elif args.cmd == "min-n":
            res = {"min_n": min_n(args.threshold, args.expected_rate, args.conf),
                   "threshold": args.threshold, "expected_rate": args.expected_rate}
        elif args.cmd == "stability":
            rows = parse_rows(args.rows) if args.rows else read_csv_rows(args.csv)
            res = stability(rows, args.threshold, args.conf, args.min_n)
        else:
            res = compare(args.k1, args.n1, args.k2, args.n2, args.conf)
    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print_human(args.cmd, res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
