#!/usr/bin/env python3
"""Bitcoin: a DTC-style EMA ribbon (TradingView "DTC - 1.3.6", DTC Trading Club) next to 60 other indicators.

    python3 dtc_btc.py run [--write]

What DTC is. "DTC - 1.3.6" is an invite-only TradingView script with hidden code. Its public page describes a
trend-following system built on a 6-layer EMA structure from 30 to 60 that sends buy and sell signals (to MT4/MT5
through PineConnector). The real script can't be read or run here, so this file tests the plainest version of
what the page describes. It is a stand-in, not the product: if the real script adds filters, they aren't here.

PRE-REGISTERED 2026-11-25, committed before any run. Not to be changed after the result:
  RIBBON: EMAs of the close with lengths 30, 36, 42, 48, 54, 60.
    up   = every EMA above the next longer one (30 > 36 > ... > 60) and the close above EMA 30
    down = every EMA below the next longer one and the close below EMA 30
    dtc_long_flat:  long while up, flat otherwise
    dtc_long_short: long while up, short while down, flat otherwise
  OTHER INDICATORS: the 60 named strategies of catalog.py (TradingView built-ins, Investopedia, classic books,
    papers), long or flat, with their textbook settings, run on Bitcoin alone.
  TIMEFRAMES: daily (Yahoo BTC-USD, 2014-09 on) for everything; the two ribbon rules also on 4-hour and 1-hour bars
    (Yahoo, the last 2 years, data/fx1h).
  FILLS: the signal from a completed bar is traded at the next bar's open.
  COSTS (Exness BTCUSD CFD, as in bot.py): 6 bp a round trip (3 bp each time the position changes side, counted
    per unit changed), plus 3 bp swap for each 00:00 UTC crossed while holding. A second line with no swap (buying
    real coins on an exchange at the same spread) is reported for the daily rules.
  STATISTIC: the rule's return minus beta x Bitcoin's return (beta from the in-sample period): its alpha over just
    holding Bitcoin. In-sample before 2020-01-01, judged from 2020-01-01 (daily). Hourly: first half in-sample,
    second half judged.
  PASS: judged alpha t >= 3.5 (Bonferroni for about 64 rules) and in-sample t > 0, with Exness costs.
  Also reported: what $500 became over the judged period next to $500 of Bitcoin held, and the worst drawdown.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import statistics
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import catalog  # noqa: E402
import daily  # noqa: E402

LENGTHS = (30, 36, 42, 48, 54, 60)
SPREAD_BPS = 6.0          # round trip
SWAP_BPS = 3.0            # per 00:00 UTC crossed
SPLIT = "2020-01-01"
T_BAR = 3.5
FX1H = os.path.join(HERE, "data", "fx1h", "BTC-USD.json.gz")
RESULT = os.path.join(HERE, "results", "dtc-btc.json")


def ribbon(c):
    """(up, down) boolean arrays for the 6-EMA ribbon; False while any EMA is still warming up."""
    e = [catalog.ema(c, n) for n in LENGTHS]
    n = len(c)
    up = np.zeros(n, bool)
    dn = np.zeros(n, bool)
    for i in range(n):
        v = [x[i] for x in e]
        if any(math.isnan(x) for x in v) or i < max(LENGTHS):
            continue
        up[i] = all(v[k] > v[k + 1] for k in range(len(v) - 1)) and c[i] > v[0]
        dn[i] = all(v[k] < v[k + 1] for k in range(len(v) - 1)) and c[i] < v[0]
    return up, dn


def positions(c):
    up, dn = ribbon(c)
    return {"dtc_long_flat": up.astype(float), "dtc_long_short": up.astype(float) - dn.astype(float)}


def returns(o, ts, pos, spread_bps=SPREAD_BPS, swap_bps=SWAP_BPS):
    """Bar returns of `pos` decided at bar t's close, held from open t+1 to open t+2. ts: epoch seconds of each
    bar's open. Cost: half the spread per unit of position change, swap per 00:00 UTC crossed while held."""
    n = len(o)
    r = np.full(n, np.nan)
    r[:-2] = o[2:] / o[1:-1] - 1.0
    p = np.asarray(pos, float)
    turn = np.abs(np.diff(p, prepend=0.0))
    nights = np.zeros(n)
    nights[:-2] = np.floor(ts[2:] / 86400) - np.floor(ts[1:-1] / 86400)
    net = p * r - turn * spread_bps / 2 / 1e4 - np.abs(p) * nights * swap_bps / 1e4
    return net, r


def tstat(x):
    x = [v for v in x if not math.isnan(v)]
    if len(x) < 3 or statistics.stdev(x) == 0:
        return 0.0
    return statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x)))


def drawdown(eq):
    peak, worst = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst


def judge(dates, net, mkt, split):
    ok = [i for i in range(len(dates)) if not math.isnan(mkt[i])]
    ins = [i for i in ok if dates[i] < split]
    jud = [i for i in ok if dates[i] >= split]
    x = np.array([mkt[i] for i in ins])
    y = np.array([net[i] for i in ins])
    beta = float(np.cov(y, x)[0, 1] / np.var(x)) if len(ins) > 30 and np.var(x) > 0 else 0.0
    a_in = [net[i] - beta * mkt[i] for i in ins]
    a_j = [net[i] - beta * mkt[i] for i in jud]
    eq, hold = [500.0], [500.0]
    for i in jud:
        eq.append(eq[-1] * (1 + net[i]))
        hold.append(hold[-1] * (1 + mkt[i]))
    out = {"beta": round(beta, 3), "is_t": round(tstat(a_in), 2), "judged_t": round(tstat(a_j), 2),
           "judged_alpha_bp": round(1e4 * statistics.mean(a_j), 2) if a_j else 0.0,
           "usd": round(eq[-1], 0), "hold_usd": round(hold[-1], 0),
           "max_dd": round(100 * drawdown(eq), 1), "hold_max_dd": round(100 * drawdown(hold), 1)}
    out["verdict"] = "PASS" if out["judged_t"] >= T_BAR and out["is_t"] > 0 else "FAIL"
    return out


def load_daily():
    D0 = daily.load("BTC-USD")
    keep = [i for i in range(len(D0["d"])) if None not in (D0["o"][i], D0["h"][i], D0["l"][i], D0["c"][i])]
    D = {k: np.array([D0[k][i] or 0.0 for i in keep], float) for k in ("o", "h", "l", "c", "v")}
    D["d"] = [D0["d"][i] for i in keep]
    D["month"] = np.array([int(d[5:7]) for d in D["d"]])
    D["ts"] = np.array([datetime.datetime.fromisoformat(d).replace(tzinfo=datetime.timezone.utc).timestamp()
                        for d in D["d"]])
    return D


def load_hourly(hours=1):
    with gzip.open(FX1H, "rt") as fh:
        a = np.array(json.load(fh), float)          # [[ts, o, h, l, c]]
    if hours > 1:
        rows = []
        for k in range(0, len(a) - hours + 1, hours):
            w = a[k:k + hours]
            if w[-1, 0] - w[0, 0] != 3600 * (hours - 1):
                continue                             # skip blocks with a gap
            rows.append([w[0, 0], w[0, 1], w[:, 2].max(), w[:, 3].min(), w[-1, 4]])
        a = np.array(rows)
    return a


def cmd_run(a):
    out = {"daily": {}, "daily_no_swap": {}, "intraday": {}}
    D = load_daily()
    print("Bitcoin daily %s to %s (%d days). In-sample before %s, judged after. Costs: Exness %.0f bp round trip "
          "+ %.0f bp a night." % (D["d"][0], D["d"][-1], len(D["d"]), SPLIT, SPREAD_BPS, SWAP_BPS))
    rules = {k: (src, pos) for k, (src, pos) in catalog.build(D).items()}
    for k, pos in positions(D["c"]).items():
        rules[k] = ("DTC-style 6-EMA ribbon 30-60 (stand-in for TradingView DTC 1.3.6)", pos)
    for name, (src, pos) in rules.items():
        net, mkt = returns(D["o"], D["ts"], pos)
        out["daily"][name] = dict(judge(D["d"], net, mkt, SPLIT), source=src)
        net0, _ = returns(D["o"], D["ts"], pos, swap_bps=0.0)
        out["daily_no_swap"][name] = judge(D["d"], net0, mkt, SPLIT)
    rows = sorted(out["daily"].items(), key=lambda kv: -kv[1]["judged_t"])
    print("\n%-24s %6s %7s %9s %8s %8s %7s %9s  %s" % ("rule (daily, long or flat)", "IS t", "judged t", "alpha bp",
                                                     "$500->", "no swap", "max DD", "", "verdict"))
    hold = rows[0][1]["hold_usd"]
    for name, r in rows:
        mark = " <- DTC" if name.startswith("dtc") else ""
        print("%-24s %+6.2f %+7.2f %+9.2f %8.0f %8.0f %6.1f%% %9s  %s" % (
            name, r["is_t"], r["judged_t"], r["judged_alpha_bp"], r["usd"], out["daily_no_swap"][name]["usd"],
            r["max_dd"], mark, r["verdict"]))
    print("Bitcoin held from %s: $500 -> $%.0f (max drawdown %.1f%%)." % (SPLIT, hold, rows[0][1]["hold_max_dd"]))
    for label, hrs in (("4-hour", 4), ("1-hour", 1)):
        A = load_hourly(hrs)
        ts = A[:, 0]
        dates = [datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H") for t in ts]
        split = dates[len(dates) // 2]
        for k, pos in positions(A[:, 4]).items():
            net, mkt = returns(A[:, 1], ts, pos)
            r = judge(dates, net, mkt, split)
            out["intraday"]["%s_%s" % (k, label)] = dict(r, range=[dates[0], dates[-1]], split=split)
            print("%-6s %-15s %s to %s, judged from %s: IS t %+.2f, judged t %+.2f, $500 -> $%.0f (held $%.0f), "
                  "max DD %.1f%%  %s" % (label, k, dates[0][:10], dates[-1][:10], split[:10], r["is_t"],
                                         r["judged_t"], r["usd"], r["hold_usd"], r["max_dd"], r["verdict"]))
    passed = [k for k, r in list(out["daily"].items()) + list(out["intraday"].items()) if r["verdict"] == "PASS"]
    out["passed"] = passed
    print("\nVerdict: %s. Research, not financial advice." % ("PASS: " + ", ".join(passed) if passed
                                                              else "FAIL: nothing passes"))
    if a.write:
        with open(RESULT, "w") as fh:
            json.dump(out, fh, indent=1)
        print("Wrote %s" % os.path.relpath(RESULT, HERE))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="DTC-style ribbon and 60 indicators on Bitcoin")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run")
    p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd != "run":
        ap.print_help()
        return 1
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
