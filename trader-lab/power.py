#!/usr/bin/env python3
"""trader-lab: how good is the paper trial's pass bar? A power and false-pass check.

    python3 power.py [--sims 4000] [--json] [--write]

The trial (paper/PLAN.md) trades the 15:30 reversal on US500, USTEC and US30 and passes after
20+ days and 30+ trades if, among others, the per-trade t >= 2. But on most signal days the
three indices move together, so 2 or 3 trades on one day are close to one bet counted 2-3 times,
which inflates a per-trade t. This file replays the exact trial rules (paper.log_day) on 4 years
of 5-minute bars (data/long, Nov 2022 on) to get the real trade distribution, then simulates
many trials by drawing whole days (keeping same-day trades together) and reports how often the
bar passes when:
  null    the true edge after costs is zero (gross shifted so the mean net per trade is 0)
  as-is   the edge is what 2022-2026 showed
  +5 bp   a real edge of 5 bp a trade after costs (a good day-trading edge)
for the current per-trade t and for a t on daily P&L (each day one observation).
Research, not financial advice.
"""

import argparse
import gzip
import json
import math
import os
import statistics
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402
import paper  # noqa: E402


def load_sessions(proxies):
    out = {}
    for p in proxies:
        with gzip.open(os.path.join(lab.LONG_STORE, p + ".json.gz"), "rt") as f:
            bars = json.load(f)
        out[p] = lab.sessions_of({k: tuple(v) if isinstance(v, (list, tuple)) else
                                  (v["o"], v["h"], v["l"], v["c"], v["v"]) for k, v in bars.items()})
    return out


def history(cfg):
    sess = load_sessions(sorted(set(cfg["instruments"].values())))
    dates = [d for d, b in sess["SPY"] if len(b) == lab.SESSION_BARS]
    days = []
    for d in dates:
        try:
            rows = paper.log_day(sess, d, cfg)
        except paper.PaperError:
            continue
        days.append([(float(r["gross_bps"]), float(r["notional_usd"])) for r in rows])
    return dates, days


def t_of(x):
    x = np.asarray(x, float)
    if len(x) < 3 or x.std(ddof=1) == 0:
        return 0.0
    return float(x.mean() / x.std(ddof=1) * math.sqrt(len(x)))


def one_trial(days, shift, cost, bar, rng):
    trades, daily, n_days = [], [], 0
    while n_days < bar["min_days"] or len(trades) < bar["min_trades"]:
        day = days[rng.integers(len(days))]
        n_days += 1
        nets = [g + shift - cost for g, _ in day]
        trades += [(n, notional) for n, notional in zip(nets, [x for _, x in day])]
        if nets:
            daily.append(sum(n * x / 1e4 for n, (_, x) in zip(nets, day)))
        if n_days > 2000:
            break
    pnl = [n * x / 1e4 for n, x in trades]
    eq = np.cumsum(pnl)
    mdd = float((np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:] - eq).max()) if len(eq) else 0.0
    base = sum(pnl) > 0 and mdd < bar["max_drawdown_usd"]
    return (base and t_of([n for n, _ in trades]) >= bar["min_t"],
            base and t_of(daily) >= bar["min_t"], n_days)


def run(sims=4000, seed=7):
    cfg = paper.load_config()
    dates, days = history(cfg)
    flat = [g for d in days for g, _ in d]
    multi = [d for d in days if len(d) >= 2]
    same_day_corr = None
    if multi:
        a = np.array([d[0][0] for d in multi])
        b = np.array([d[1][0] for d in multi])
        same_day_corr = float(np.corrcoef(a, b)[0, 1])
    cost = cfg["cost_bps"]
    mean_net = statistics.mean(flat) - cost
    rng = np.random.default_rng(seed)
    out = {"from": dates[0], "to": dates[-1], "days": len(days), "signal_days": sum(1 for d in days if d),
           "trades": len(flat), "mean_net_bps": mean_net, "sd_bps": statistics.stdev(flat),
           "trades_per_signal_day": len(flat) / max(1, sum(1 for d in days if d)),
           "same_day_corr": same_day_corr, "per_trade_t_hist": t_of([g - cost for g in flat]),
           "scenarios": {}}
    for name, shift in (("null", -mean_net), ("as-is", 0.0), ("+5 bp", 5.0 - mean_net)):
        res = [one_trial(days, shift, cost, cfg["pass_bar"], rng) for _ in range(sims)]
        out["scenarios"][name] = {"pass_per_trade_t": float(np.mean([r[0] for r in res])),
                                  "pass_daily_t": float(np.mean([r[1] for r in res])),
                                  "median_days": float(np.median([r[2] for r in res]))}
    return out


def report(r):
    print("Paper-trial bar check: the trial's rules replayed on %s to %s (%d sessions, 5-minute bars)." % (
        r["from"], r["to"], r["days"]))
    print("  %d signal days, %d trades (%.1f a signal day); net %.2f bp a trade at the assumed cost, sd %.1f bp; "
          "per-trade t over 4 years %.2f." % (r["signal_days"], r["trades"], r["trades_per_signal_day"],
                                              r["mean_net_bps"], r["sd_bps"], r["per_trade_t_hist"]))
    if r["same_day_corr"] is not None:
        print("  Same-day trades move together: correlation %.2f between a day's first two trades." % r["same_day_corr"])
    print("  How often the bar (20+ days, 30+ trades, net > 0, t >= 2, drawdown < $60) passes:")
    for k, s in r["scenarios"].items():
        print("    %-6s  per-trade t: %5.1f%%   daily t: %5.1f%%   (trial length: median %.0f days)" % (
            k, 100 * s["pass_per_trade_t"], 100 * s["pass_daily_t"], s["median_days"]))
    print("Research, not financial advice.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="power and false-pass check of the paper-trial bar")
    ap.add_argument("--sims", type=int, default=4000)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    r = run(a.sims)
    if a.write:
        with open(os.path.join(HERE, "results", "power.json"), "w") as f:
            json.dump(r, f, indent=1)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        report(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
