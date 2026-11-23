#!/usr/bin/env python3
"""The volatility risk premium: short VIX futures (SVXY) only when the VIX curve is in contango.

    python3 vrp.py fetch            # ^VIX, ^VIX3M, SVXY, SPY (dividend-adjusted) from Yahoo into data/alloc
    python3 vrp.py test [--write]

Why: option buyers pay for crash insurance, so implied volatility sits above realized volatility
most of the time (Carr & Wu 2009). Short VIX-futures funds harvest that premium. Simon & Campasano
(2014, "The VIX Futures Basis: Evidence and Trading Strategies") report it pays mainly when the
curve is in contango (spot VIX below longer-dated VIX). The premium has an economic reason to
persist (it is insurance). The risk is known too: on 2018-02-05 short-volatility funds lost about
80-90% in a day.

PRE-REGISTERED 2026-11-23, before any result was seen. Not to be changed after the first run:

  Instrument: SVXY (ProShares Short VIX Short-Term Futures). It was -1x until 2018-02-27 and has
  been -0.5x since; both regimes are tested as they happened (that is what a holder got).
  Signal at day t's close, traded at day t+1's close, held to the next trade (one day of delay).
  Cash earns the 13-week T-bill. Cost: 10 bps per unit of turnover, re-run at 20 bps.
  Rules (variant chosen on IS Sharpe only):
    V1 contango  hold SVXY when ^VIX / ^VIX3M < k, else cash. k in 0.90, 0.95, 1.00.
    V2 trend     V1 with k = 1.00, and only when SPY closes above its 200-day average. (no grid)
  Periods: IS 2011-10 to 2017-12 (the -1x years, no blow-up), OOS 2018-2021 (contains
  2018-02-05 and 2020-03), HOLDOUT 2022 on.
  Benchmarks: SPY buy-and-hold for the standalone rule; for a portfolio use, 80% SPY + 20% rule
  (monthly rebalanced) vs 100% SPY.
  PASS (standalone): Sharpe > SPY's in OOS and HOLDOUT separately, at 10 AND 20 bps; stationary
  bootstrap p < 0.05 / 2 (two rules) that the post-IS Sharpe beats SPY's; time-shift placebo
  p < 0.05 (the same daily positions slid in time).
  PASS (sleeve): the 80/20 portfolio's post-IS Sharpe > SPY's with bootstrap p < 0.025 and its max
  drawdown no worse than SPY's + 5 points.
  Report max drawdown and the worst day for everything: a premium that can lose 80% in a day must
  show that number up front.
Caveats up front: SVXY's history is one fund (no survivorship issue, but its leverage changed);
VIX3M history starts 2007-12, so the test starts with SVXY in 2011-10. Research, not financial advice.
"""

import argparse
import bisect
import datetime
import json
import math
import os
import random
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc  # noqa: E402  (adjusted-close parsing, storage, bootstrap)
import daily  # noqa: E402  (Yahoo fetch)

SYMS = ["^VIX", "^VIX3M", "SVXY", "SPY", "^IRX"]
IS_END, OOS_END = "2017-12-31", "2021-12-31"
COSTS = (10.0, 20.0)
N_RULES = 2


def cmd_fetch(a):
    os.makedirs(alloc.STORE, exist_ok=True)
    import gzip
    for s in SYMS:
        D = alloc.parse_adj(daily.fetch_daily(s))
        tmp = alloc.path(s) + ".tmp"
        with gzip.GzipFile(tmp, "wb", mtime=0) as gz:
            gz.write(json.dumps(D, separators=(",", ":")).encode("utf-8"))
        os.replace(tmp, alloc.path(s))
        print("%-7s %5d days %s to %s" % (s, len(D["d"]), D["d"][0], D["d"][-1]))
        time.sleep(daily.PAUSE)
    return 0


class Days:
    """Daily panel on SVXY's calendar; all series aligned by last-known value."""

    def __init__(self, data):
        self.data = data
        self.d = data["SVXY"]["d"]

    def v(self, sym, date):
        return alloc.value_on(self.data[sym], date)

    def sma200_above(self, date):
        D = self.data["SPY"]
        k = bisect.bisect_right(D["d"], date) - 1
        if k < 199:
            return None
        return D["c"][k] > sum(D["c"][k - 199:k + 1]) / 200.0

    def cash(self, d0, d1):
        y = self.v("^IRX", d0) or 0.0
        return y / 100.0 * (datetime.date.fromisoformat(d1) - datetime.date.fromisoformat(d0)).days / 360.0


def sig_contango(P, date, p):
    a, b = P.v("^VIX", date), P.v("^VIX3M", date)
    return None if not (a and b) else (1.0 if a / b < p["k"] else 0.0)


def sig_trend(P, date, p):
    s = sig_contango(P, date, {"k": 1.0})
    up = P.sma200_above(date)
    return None if s is None or up is None else (s if up else 0.0)


RULES = {"contango": (sig_contango, [{"k": k} for k in (0.90, 0.95, 1.00)], "Simon & Campasano 2014"),
         "trend": (sig_trend, [{}], "contango + SPY 200-day filter")}


def simulate(P, fn, p, cost_bps):
    """Daily rows (date, return, cash, weight). Signal at d[i] close, trade at d[i+1] close,
    held to d[i+2] close."""
    rows, prev = [], 0.0
    for i in range(len(P.d) - 2):
        w = fn(P, P.d[i], p)
        if w is None:
            continue
        d0, d1 = P.d[i + 1], P.d[i + 2]
        a, b = P.v("SVXY", d0), P.v("SVXY", d1)
        c = P.cash(d0, d1)
        r = w * (b / a - 1) + (1 - w) * c - abs(w - prev) * cost_bps / 1e4
        rows.append((d0, r, c, w))
        prev = w
    return rows


def bh(P, sym, start):
    rows = []
    for i in range(len(P.d) - 1):
        d0, d1 = P.d[i], P.d[i + 1]
        if d0 < start:
            continue
        a, b = P.v(sym, d0), P.v(sym, d1)
        rows.append((d0, b / a - 1, P.cash(d0, d1), 1.0))
    return rows


def sleeve(rule_rows, spy_rows, share=0.2):
    """80% SPY + 20% rule, rebalanced at each month's first day (drift in between)."""
    spy = {d: (r, c) for d, r, c, _ in spy_rows}
    out, ws, wr, month = [], 1 - share, share, None
    for d, r, c, _ in rule_rows:
        if d not in spy:
            continue
        if d[:7] != month:
            ws, wr, month = 1 - share, share, d[:7]
        rs = spy[d][0]
        tot = ws * (1 + rs) + wr * (1 + r)
        out.append((d, tot - 1, c, 1.0))
        ws, wr = ws * (1 + rs) / tot, wr * (1 + r) / tot
    return out


def dstats(rows):
    if len(rows) < 60:
        return {"n": len(rows), "sharpe": float("nan"), "cagr": float("nan"), "mdd": float("nan"), "worst": float("nan")}
    ex = [r - c for _, r, c, _ in rows]
    sd = statistics.pstdev(ex)
    g, peak, mdd = 1.0, 1.0, 0.0
    for _, r, _, _ in rows:
        g *= 1 + r
        peak = max(peak, g)
        mdd = min(mdd, g / peak - 1)
    return {"n": len(rows), "sharpe": statistics.mean(ex) / sd * math.sqrt(252) if sd > 0 else float("nan"),
            "cagr": g ** (252.0 / len(rows)) - 1, "mdd": mdd, "worst": min(r for _, r, _, _ in rows),
            "invested": statistics.mean(w for *_, w in rows)}


def dsharpe(ex):
    sd = statistics.pstdev(ex) if len(ex) > 1 else 0
    return statistics.mean(ex) / sd * math.sqrt(252) if sd > 0 else 0.0


def boot_p(ex_s, ex_b, draws=1000, block=20, seed=7):
    rnd = random.Random(seed)
    n = len(ex_s)
    bad = 0
    for _ in range(draws):
        idx, i = [], rnd.randrange(n)
        while len(idx) < n:
            idx.append(i)
            i = rnd.randrange(n) if rnd.random() < 1.0 / block else (i + 1) % n
        if dsharpe([ex_s[j] for j in idx]) - dsharpe([ex_b[j] for j in idx]) <= 0:
            bad += 1
    return bad / draws


def shift_placebo_p(P, rows, cost_bps, step=5):
    """Circular shifts (every `step` days) of the daily position series against the same days'
    SVXY returns: the share that reach the real Sharpe."""
    n = len(rows)
    nxt = {P.d[i]: P.d[i + 1] for i in range(len(P.d) - 1)}
    rs = [P.v("SVXY", nxt[d]) / P.v("SVXY", d) - 1 for d, *_ in rows]
    cs = [c for _, _, c, _ in rows]
    W = [w for *_, w in rows]
    real = dsharpe([r - c for _, r, c, _ in rows])
    hits = tries = 0
    for sh in range(step, n, step):
        ex, prev = [], W[sh % n]
        for i in range(n):
            w = W[(i + sh) % n]
            ex.append(w * rs[i] + (1 - w) * cs[i] - abs(w - prev) * cost_bps / 1e4 - cs[i])
            prev = w
        tries += 1
        hits += dsharpe(ex) >= real
    return hits / tries if tries else float("nan")


def part(rows, lo, hi=None):
    return [x for x in rows if x[0] > lo and (hi is None or x[0] <= hi)]


def cmd_test(a):
    data = {s: alloc.load(s) for s in SYMS}
    missing = [s for s, D in data.items() if not D]
    if missing:
        raise daily.LabError("missing %s: run `vrp.py fetch`" % ", ".join(missing))
    P = Days(data)
    report = {"run": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rules": {}}
    print("Short volatility (SVXY) with a contango filter. IS to 2017, OOS 2018-2021, HOLDOUT 2022+.")
    print("Benchmark SPY buy-and-hold (dividend-adjusted); sleeve = 80% SPY + 20% rule.\n")
    for name, (fn, grid, src) in RULES.items():
        best = None
        for p in grid:
            s = dstats([x for x in simulate(P, fn, p, COSTS[0]) if x[0] <= IS_END])
            if best is None or s["sharpe"] > best[1]["sharpe"]:
                best = (p, s)
        p, s_is = best
        res = {"source": src, "params": p, "is": s_is}
        ok = {}
        for cost in COSTS:
            rows = simulate(P, fn, p, cost)
            spy = bh(P, "SPY", rows[0][0])
            post, spost = part(rows, IS_END), part(spy, IS_END)
            sdates = {x[0]: x for x in spost}
            pair = [(x, sdates[x[0]]) for x in post if x[0] in sdates]
            sl = part(sleeve(rows, spy), IS_END)
            sl_pair = [(x, sdates[x[0]]) for x in sl if x[0] in sdates]
            r = {"oos": dstats(part(rows, IS_END, OOS_END)), "holdout": dstats(part(rows, OOS_END)),
                 "post": dstats(post), "spy_oos": dstats(part(spy, IS_END, OOS_END)),
                 "spy_holdout": dstats(part(spy, OOS_END)), "spy_post": dstats(spost),
                 "boot_p": boot_p([x[1] - x[2] for x, _ in pair], [y[1] - y[2] for _, y in pair]),
                 "placebo_p": shift_placebo_p(P, post, cost),
                 "sleeve_post": dstats(sl),
                 "sleeve_boot_p": boot_p([x[1] - x[2] for x, _ in sl_pair], [y[1] - y[2] for _, y in sl_pair])}
            res["cost_%d" % cost] = r
            ok[cost] = (r["oos"]["sharpe"] > r["spy_oos"]["sharpe"] and r["holdout"]["sharpe"] > r["spy_holdout"]["sharpe"]
                        and r["boot_p"] < 0.05 / N_RULES and r["placebo_p"] < 0.05,
                        r["sleeve_post"]["sharpe"] > r["spy_post"]["sharpe"] and r["sleeve_boot_p"] < 0.025
                        and r["sleeve_post"]["mdd"] >= r["spy_post"]["mdd"] - 0.05)
        res["verdict"] = "PASS" if ok[10.0][0] and ok[20.0][0] else "FAIL"
        res["sleeve_verdict"] = "PASS" if ok[10.0][1] and ok[20.0][1] else "FAIL"
        report["rules"][name] = res
        r = res["cost_20"]
        print("%-9s %-12s IS Sh %5.2f | post-IS @20bp: Sh %5.2f (SPY %5.2f)  CAGR %6.1f%% (SPY %5.1f%%)  maxDD %6.1f%% (SPY %5.1f%%)"
              "  worst day %6.1f%%  in %3.0f%%" % (name, json.dumps(p), s_is["sharpe"], r["post"]["sharpe"], r["spy_post"]["sharpe"],
                                               100 * r["post"]["cagr"], 100 * r["spy_post"]["cagr"], 100 * r["post"]["mdd"],
                                               100 * r["spy_post"]["mdd"], 100 * r["post"]["worst"], 100 * r["post"]["invested"]))
        print("          OOS Sh %5.2f (SPY %5.2f)  HOLDOUT Sh %5.2f (SPY %5.2f)  boot p %.3f  placebo p %.3f  -> %s" % (
            r["oos"]["sharpe"], r["spy_oos"]["sharpe"], r["holdout"]["sharpe"], r["spy_holdout"]["sharpe"],
            r["boot_p"], r["placebo_p"], res["verdict"]))
        print("          sleeve 80/20: Sh %5.2f  CAGR %5.1f%%  maxDD %6.1f%%  boot p %.3f  -> %s" % (
            r["sleeve_post"]["sharpe"], 100 * r["sleeve_post"]["cagr"], 100 * r["sleeve_post"]["mdd"],
            r["sleeve_boot_p"], res["sleeve_verdict"]))
    print("\nResearch, not financial advice.")
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True, default=str)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    p = sub.add_parser("test")
    p.add_argument("--write", nargs="?", const=os.path.join(alloc.RESULTS, "vrp.json"))
    a = ap.parse_args(argv)
    try:
        return {"fetch": cmd_fetch, "test": cmd_test}[a.cmd](a) if a.cmd else ap.print_help() or 1
    except daily.LabError as e:
        print("vrp.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
