#!/usr/bin/env python3
"""Pairs trading on ETFs, the distance method of Gatev, Goetzmann & Rouwenhorst (2006). Pre-registered.

    python3 pairs.py run [--write]   # Yahoo adjusted closes (data/paper500 cache) -> results/pairs.json

The idea: two funds that have moved together for a year will come back together when they drift apart.
GGR (2006, RFS) found about 11% a year on US stocks 1962-2002 and reported that profits fell after the 1990s.
The owner asked for more research; this hasn't been tested here before.

PRE-REGISTERED 2026-11-25, committed before any result. Not to be changed:
  Universe: the 60 ETFs in UNIVERSE below (index, sector, country, bond, commodity, industry), adjusted closes.
    A fund is eligible for a formation window only if it has every day of that window.
  Formation: the 252 trading days before the trading start. Prices are scaled to 1 at the window's start; the
    distance of a pair is the sum of squared differences of the scaled prices. The 20 closest pairs are chosen.
  Trading: the next 126 trading days. The spread (scaled A minus scaled B, scaling kept from the formation
    window) is checked at each close. When it is more than 2 formation standard deviations from 0, the trade
    opens at the NEXT close (GGR's one-day wait): $1 long the cheap fund, $1 short the dear one. It closes at the
    next close after the spread crosses 0, or on the last trading day. A pair can reopen after it closes.
  A new portfolio starts on the first trading day of every month; six overlap. The strategy's daily return is the
    mean of the active portfolios' returns, each = total pair P&L / 20 (committed capital, as GGR).
  Costs: 5 bps per leg per trade (so 20 bps a round trip per pair); 10 bps reported. Short borrow fees ignored.
  Control: 20 random pairs from the same eligible funds (fixed seed), same rules: reported only.
  Split: trading starts from 2000-01 in-sample before 2015-01-01, judged from 2015-01-01.
  Verdict: PASS only if judged monthly mean t >= 3 and the in-sample mean is positive.
  Reported: $500 compounded on the judged years next to $500 in SPY.
Research, not financial advice.
"""

import argparse
import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paper500 as p5  # noqa: E402

RESULTS = os.path.join(HERE, "results")
UNIVERSE = ["SPY", "QQQ", "DIA", "IWM", "MDY",
            "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
            "EWJ", "EWG", "EWU", "EWC", "EWA", "EWH", "EWS", "EWT", "EWY", "EWZ", "EWW", "EWP", "EWI", "EWQ",
            "EWL", "EWN", "EWD", "EZA", "EWM", "EEM", "EFA", "VGK", "FXI",
            "TLT", "IEF", "SHY", "LQD", "TIP", "HYG", "EMB",
            "GLD", "SLV", "GDX", "USO", "DBC",
            "VNQ", "IYR", "XBI", "IBB", "SMH", "KRE", "XHB", "XRT", "ITB", "OIH", "XME"]
FORM, TRADE, NPAIRS, ENTRY_SD = 252, 126, 20, 2.0
COST_BPS, REF_COST_BPS = 5.0, 10.0
START, SPLIT, T_BAR = "2000-01-01", "2015-01-01", 3.0
SEED = 2006


def load():
    px = {}
    for s in UNIVERSE:
        b = p5.prices(s)
        if b:
            px[s] = dict(zip(b["d"], b["a"]))
    cal = sorted(px["SPY"])
    return cal, px


def choose(cal, px, t0, rng=None):
    """Eligible funds over [t0-FORM, t0); the NPAIRS closest pairs (or random ones) with their scaling and sd."""
    w = cal[t0 - FORM:t0]
    names = [s for s in UNIVERSE if s in px and all(d in px[s] for d in w)]
    norm = {s: [px[s][d] / px[s][w[0]] for d in w] for s in names}
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    if rng is not None:
        pick = rng.sample(pairs, min(NPAIRS, len(pairs)))
    else:
        pick = sorted(pairs, key=lambda p: sum((x - y) ** 2 for x, y in zip(norm[p[0]], norm[p[1]])))[:NPAIRS]
    out = []
    for a, b in pick:
        sp = [x - y for x, y in zip(norm[a], norm[b])]
        out.append({"a": a, "b": b, "base_a": px[a][w[0]], "base_b": px[b][w[0]], "sd": statistics.pstdev(sp)})
    return out


def trade_pair(cal, px, t0, p, cost_bps):
    """Daily P&L (per $1 a leg) of one pair over [t0, t0+TRADE)."""
    days = cal[t0:t0 + TRADE]
    pnl = [0.0] * len(days)
    pos = 0          # +1: long a / short b; -1: long b / short a
    pending = None   # "open+1", "open-1" or "close", executed at the next close
    ent = None
    last = None
    for i, d in enumerate(days):
        pa, pb = px[p["a"]].get(d), px[p["b"]].get(d)
        if pa is None or pb is None:          # a fund stopped trading: close at its last price
            pending = None
            if pos:
                pos = 0
            continue
        if pos and last:                      # mark to market
            ra, rb = pa / last[0] - 1, pb / last[1] - 1
            pnl[i] += pos * (ra * ent[0] - rb * ent[1])
            ent = (ent[0] * (1 + ra), ent[1] * (1 + rb))
        if pending == "close" and pos:
            pnl[i] -= 2 * cost_bps / 1e4
            pos, pending = 0, None
        elif pending in ("open+1", "open-1") and not pos:
            pos = 1 if pending == "open+1" else -1
            ent = (1.0, 1.0)
            pnl[i] -= 2 * cost_bps / 1e4
            pending = None
        last = (pa, pb)
        s = pa / p["base_a"] - pb / p["base_b"]
        if i == len(days) - 1:
            if pos:
                pnl[i] -= 2 * cost_bps / 1e4
                pos = 0
            break
        if pos == 0 and p["sd"] > 0 and abs(s) > ENTRY_SD * p["sd"]:
            pending = "open+1" if s < 0 else "open-1"    # a cheap: long a
        elif pos and ((pos > 0 and s >= 0) or (pos < 0 and s <= 0)):
            pending = "close"
    return dict(zip(days, pnl))


def strategy(cal, px, cost_bps, random_pairs=False):
    """{date: daily return} averaged over the active monthly portfolios."""
    rng = random.Random(SEED) if random_pairs else None
    starts = [i for i in range(FORM, len(cal)) if cal[i] >= START and cal[i][:7] != cal[i - 1][:7]]
    acc = {}
    for t0 in starts:
        pairs = choose(cal, px, t0, rng)
        if not pairs:
            continue
        port = {}
        for p in pairs:
            for d, v in trade_pair(cal, px, t0, p, cost_bps).items():
                port[d] = port.get(d, 0.0) + v / NPAIRS
        for d, v in port.items():
            acc.setdefault(d, []).append(v)
    return {d: sum(v) / len(v) for d, v in sorted(acc.items())}


def monthly_of(daily):
    m = {}
    for d, r in daily.items():
        m[d[:7]] = m.get(d[:7], 1.0) * (1 + r)
    return {k: v - 1 for k, v in sorted(m.items())}


def summary(mon, lo=None, hi=None):
    x = [v for k, v in mon.items() if (lo is None or k >= lo[:7]) and (hi is None or k < hi[:7])]
    if len(x) < 2:
        return {"months": len(x), "mean_pct": 0.0, "t": 0.0}
    return {"months": len(x), "mean_pct": 100 * statistics.mean(x),
            "t": statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x))),
            "annual_pct": 100 * (math.prod(1 + v for v in x) ** (12 / len(x)) - 1)}


def usd(daily, lo):
    v = 500.0
    for d, r in daily.items():
        if d >= lo:
            v *= 1 + r
    return v


def cmd_run(a):
    cal, px = load()
    main_d = strategy(cal, px, COST_BPS)
    ref_d = strategy(cal, px, REF_COST_BPS)
    rnd_d = strategy(cal, px, COST_BPS, random_pairs=True)
    res = {}
    for name, d in (("pairs", main_d), ("pairs_10bp", ref_d), ("random_pairs", rnd_d)):
        mon = monthly_of(d)
        res[name] = {"in_sample": summary(mon, hi=SPLIT), "judged": summary(mon, lo=SPLIT), "usd_judged": usd(d, SPLIT)}
        print("%-13s | IS %3d mo %+.2f%%/mo t %+5.2f | judged %3d mo %+.2f%%/mo t %+5.2f (%.1f%%/yr) | $500 -> $%.0f since 2015" % (
            name, res[name]["in_sample"]["months"], res[name]["in_sample"]["mean_pct"], res[name]["in_sample"]["t"],
            res[name]["judged"]["months"], res[name]["judged"]["mean_pct"], res[name]["judged"]["t"],
            res[name]["judged"].get("annual_pct", 0), res[name]["usd_judged"]))
    spy = [d for d in cal if d >= SPLIT and d <= max(main_d)]
    res["spy_usd_judged"] = 500.0 * px["SPY"][spy[-1]] / px["SPY"][spy[0]] if spy else None
    m = res["pairs"]
    res["verdict"] = "PASS" if (m["judged"]["t"] >= T_BAR and m["in_sample"]["mean_pct"] > 0) else "FAIL"
    print("SPY held: $500 -> $%.0f | verdict: %s" % (res["spy_usd_judged"] or 0, res["verdict"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "pairs.json"))
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
