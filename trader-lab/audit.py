#!/usr/bin/env python3
"""trader-lab audit: independent checks of the daily engine's passing rules.

    python3 audit.py              # all checks
    python3 audit.py --placebos 200

Checks, each written from scratch here (not calling daily.py's rule code):
  1. independent re-implementation of Double 7s and RSI(2) -> same trades as daily.py?
  2. RSI definition: Connors uses Wilder's RSI; daily.py used a simple-average (Cutler) RSI.
  3. placebo: random entries with the same number of trades and the same holding times.
     A long-only rule in a rising market makes money with no skill; the real rule has to beat this.
  4. survivorship: the stock list is today's survivors (NVDA, AVGO...); rerun on ETFs only.
  5. costs: 2, 5 and 10 bps per trade.
  6. lookahead: delay every signal by one day. A real edge should weaken, never improve.
"""

import argparse
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402  (data loading and the stats helpers only)

ETFS = ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI",
        "XLU", "XLB", "SMH", "TLT", "GLD", "EEM", "EFA"]
POST = "2014-12-31"


# ---------------------------------------------------------------- independent indicators

def wilder_rsi(c, n):
    """Wilder's RSI, as in Connors: seed with a simple average, then smooth with alpha = 1/n."""
    out = [None] * len(c)
    if len(c) <= n:
        return out
    gains = [max(c[i] - c[i - 1], 0) for i in range(1, n + 1)]
    losses = [max(c[i - 1] - c[i], 0) for i in range(1, n + 1)]
    ag, al = sum(gains) / n, sum(losses) / n
    for i in range(n, len(c)):
        if i > n:
            ch = c[i] - c[i - 1]
            ag = (ag * (n - 1) + max(ch, 0)) / n
            al = (al * (n - 1) + max(-ch, 0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def cutler_rsi(c, n):
    out = [None] * len(c)
    for i in range(n, len(c)):
        up = sum(max(c[k] - c[k - 1], 0) for k in range(i - n + 1, i + 1))
        dn = sum(max(c[k - 1] - c[k], 0) for k in range(i - n + 1, i + 1))
        out[i] = 50.0 if up + dn == 0 else 100 * up / (up + dn)
    return out


def sma_at(c, i, n):
    return sum(c[i - n + 1:i + 1]) / n if i >= n - 1 else None


# ---------------------------------------------------------------- independent simulator

def simulate(D, signal, exit_rule, fill="open", max_days=30, delay=0):
    """Long-only. signal[i] True at the close of day i. Enter at the next open (fill='open') or that
    close. exit_rule(i_entry, k) True at the close of day k. Returns trades as
    (entry_date_index, exit_index, gross return)."""
    c, o = D["c"], D["o"]
    n = len(c)
    trades = []
    i = 0
    while i < n - 1 - delay:
        s = i
        if not signal[i]:
            i += 1
            continue
        s = i + delay
        if s >= n - 1:
            break
        px = o[s + 1] if fill == "open" else c[s]
        k = s + 1
        while k < n - 1 and not exit_rule(s, k) and k - s < max_days:
            k += 1
        trades.append((s, k, c[k] / px - 1, px))
        i = k  # flat after the exit close; a signal on the exit day can re-enter
    return trades


def daily_series(trades_by_sym, universe, cost_bps, mtm=True):
    """Mark each trade to market day by day (like daily.py), equal weight across open trades,
    0 on flat days. -> {date: bps}."""
    by_day = {}
    for sym, trades in trades_by_sym.items():
        D = universe[sym]
        c, o, d = D["c"], D["o"], D["d"]
        for tr in trades:
            s, k = tr[0], tr[1]
            entry_px = tr[3] if len(tr) > 3 else c[s]
            for t in range(s + 1, k + 1):
                base = entry_px if t == s + 1 else c[t - 1]
                r = (c[t] / base - 1) * 1e4
                if t == k:
                    r -= cost_bps
                by_day.setdefault(d[t], []).append(r)
    return by_day


def post_stats(by_day, dates):
    x = [statistics.mean(by_day[d]) if d in by_day else 0.0 for d in dates if d > POST]
    return daily.stats(x)


# ---------------------------------------------------------------- rules (independent code)

def rules(D, rsi_kind):
    c = D["c"]
    n = len(c)
    rsi = (wilder_rsi if rsi_kind == "wilder" else cutler_rsi)(c, 2)
    sma200 = [sma_at(c, i, 200) for i in range(n)]
    sma5 = [sma_at(c, i, 5) for i in range(n)]
    d7 = [i >= 199 and c[i] > sma200[i] and c[i] <= min(c[i - 6:i + 1]) for i in range(n)]
    r2 = [i >= 199 and rsi[i] is not None and rsi[i] < 10 and c[i] > sma200[i] for i in range(n)]
    r3 = [False] * n
    for i in range(203, n):
        w = rsi[i - 3:i + 1]
        if None in w or sma200[i] is None:
            continue
        r3[i] = (c[i] > sma200[i] and w[0] < 60 and w[0] > w[1] > w[2] > w[3] and w[3] < 10)
    return {
        "r3": (r3, lambda s, k: rsi[k] is not None and rsi[k] > 70),
        "double7": (d7, lambda s, k: c[k] >= max(c[k - 6:k + 1])),
        "rsi2_sma5": (r2, lambda s, k: c[k] > sma5[k]),
        "rsi2_rsi70": (r2, lambda s, k: rsi[k] is not None and rsi[k] > 70),
    }


def run(universe, rsi_kind, fill, cost, delay=0, only=None):
    out = {}
    for name in ("r3", "double7", "rsi2_sma5", "rsi2_rsi70"):
        if only and name not in only:
            continue
        tb = {}
        for sym, D in universe.items():
            sig, ex = rules(D, rsi_kind)[name]
            tb[sym] = simulate(D, sig, ex, fill=fill, delay=delay)
        out[name] = tb
    return out


def placebo(universe, trades_by_sym, dates, cost, reps, seed=11):
    """Same trades per symbol and the same holding lengths, at random start days."""
    rnd = random.Random(seed)
    res = []
    for _ in range(reps):
        tb = {}
        for sym, trades in trades_by_sym.items():
            n = len(universe[sym]["c"])
            fake = []
            D = universe[sym]
            for tr in trades:
                L = tr[1] - tr[0]
                s2 = rnd.randrange(200, n - L - 1)
                fake.append((s2, s2 + L, 0.0, D["o"][s2 + 1]))
            tb[sym] = fake
        res.append(post_stats(daily_series(tb, universe, cost), dates))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--placebos", type=int, default=100)
    a = ap.parse_args(argv)
    uni = daily.load_universe(daily.UNIVERSE)
    dates = sorted({d for D in uni.values() for d in D["d"]})

    print("1+2. Independent re-implementation, next-open fills, 2 bps, post-2014 (t, mean bp/day, trades):")
    base = {}
    for kind in ("cutler", "wilder"):
        r = run(uni, kind, "open", 2.0)
        for name, tb in r.items():
            st = post_stats(daily_series(tb, uni, 2.0), dates)
            n = sum(len(t) for t in tb.values())
            print("   %-6s RSI  %-11s t %5.2f  mean %5.2f  trades %6d" % (kind, name, st["t"], st["mean"], n))
            if kind == "wilder":
                base[name] = tb

    print("\n3. Placebo: random entries, same count and holding times (%d draws), post-2014 t:" % a.placebos)
    for name, tb in base.items():
        real = post_stats(daily_series(tb, uni, 2.0), dates)
        pl = placebo(uni, tb, dates, 2.0, a.placebos)
        ts = sorted(p["t"] for p in pl)
        beat = sum(1 for p in pl if p["t"] >= real["t"]) / float(len(pl))
        print("   %-11s real t %5.2f | placebo median %5.2f, 95th pct %5.2f | share of placebos >= real: %.2f" % (
            name, real["t"], ts[len(ts) // 2], ts[int(0.95 * (len(ts) - 1))], beat))

    print("\n4. Survivorship: ETFs only (19 funds), Wilder RSI, next-open, 2 bps, post-2014:")
    etf = {s: D for s, D in uni.items() if s in ETFS}
    for name, tb in run(etf, "wilder", "open", 2.0).items():
        st = post_stats(daily_series(tb, etf, 2.0), dates)
        print("   %-11s t %5.2f  mean %5.2f bp/day" % (name, st["t"], st["mean"]))

    print("\n5. Costs per trade (Wilder, next-open, all 40), post-2014 t:")
    for cost in (2.0, 5.0, 10.0):
        row = []
        for name, tb in base.items():
            row.append("%s %5.2f" % (name, post_stats(daily_series(tb, uni, cost), dates)["t"]))
        print("   %4.0f bps: %s" % (cost, " | ".join(row)))

    print("\n6. Lookahead check: every signal delayed one day (should weaken):")
    for name, tb in run(uni, "wilder", "open", 2.0, delay=1).items():
        st = post_stats(daily_series(tb, uni, 2.0), dates)
        print("   %-11s t %5.2f (vs on-time above)" % (name, st["t"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
