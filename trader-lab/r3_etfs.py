#!/usr/bin/env python3
"""Connors R3 on a wide, fresh ETF set (idea queue item 1).

    python3 r3_etfs.py fetch                 # daily bars from Yahoo into data/daily (gitignored)
    python3 r3_etfs.py test [--placebos 1000]

Why: on the lab's 40 symbols R3 passed every gate, but on the 19 ETFs alone it failed (t 1.53,
placebo p 0.31). The 21 stocks are today's survivors, so the stock trades may be survivorship
luck. This test asks whether R3 beats random entry on ETFs the lab has never used.

PRE-REGISTERED before any result was seen (2026-11-23). Not to be changed after the run:
  * Rule: Connors R3 exactly as in audit.py (independent code): close above the 200-day SMA,
    Wilder RSI(2) falling 3 days in a row from below 60 to below 10; buy the next open; sell at
    the close when RSI(2) > 70 (30-day time stop). Long only. Equal weight across open trades.
  * Test set: NEW_ETFS below, which excludes the 19 ETFs the lab already used. Inverse ETFs are
    excluded (long-only logic). Leveraged funds are reported but are NOT part of the test set,
    because a 2x/3x fund is the same bet as its index.
  * Periods: full history (from each fund's 200th day) and post-2014.
  * Benchmark: 1,000 placebos per period: random entry days in the same fund, the same number of
    trades and the same holding lengths.
  * PASS only if, on NEW_ETFS: placebo p < 0.05 in BOTH periods, AND t >= 2 at 5 bps per trade
    in both periods, AND R3 beats its placebo median in at least 3 of the 5 categories (post-2014).
    Anything less is a FAIL and R3 stays unproven.
Caveat stated up front: Yahoo has no closed or delisted ETFs, so this is survivor-light, not
survivor-free; ETFs rarely go to zero, which is why they are the better test. Prices are
split-adjusted, not dividend-adjusted (a fund's ex-dividend drop can look like a dip).
"""

import argparse
import os
import random
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402  (data fetch/load and stats only)
import audit  # noqa: E402  (independent R3, simulator, placebo)

CATEGORIES = {
    "us_equity": ["VTI", "IJR", "IWD", "IWF", "IWN", "IWO", "RSP", "OEF", "VTV", "VUG", "IJH", "IJJ",
                  "IJK", "IJS", "IJT", "MTUM", "USMV"],
    "us_industry": ["IBB", "XBI", "KRE", "KBE", "XHB", "ITB", "XRT", "XME", "XOP", "OIH", "IYR", "IYT",
                    "VNQ", "ITA", "IGV", "SOXX", "IYZ", "XLRE", "XLC", "KIE", "IHI", "PBW", "TAN", "JETS"],
    "intl_equity": ["EWJ", "EWG", "EWU", "EWC", "EWA", "EWZ", "EWW", "EWH", "EWS", "EWT", "EWY", "EWI",
                    "EWP", "EWQ", "EWL", "EWN", "EWD", "EWK", "EWO", "EZA", "FXI", "INDA", "ILF", "EWM",
                    "VGK", "VWO", "ACWI", "EFV", "SCZ", "EWX", "THD", "TUR", "ECH", "EPOL", "GXC"],
    "bonds": ["IEF", "SHY", "LQD", "HYG", "TIP", "AGG", "BND", "EMB", "MUB", "JNK", "IEI", "TLH",
              "MBB", "BNDX", "PFF", "CWB"],
    "commod_fx": ["SLV", "USO", "UNG", "DBA", "DBC", "UUP", "FXE", "FXY", "FXA", "FXB", "FXC", "GDX",
                  "GDXJ", "IAU", "PPLT", "CPER", "DBB", "DBO"],
}
LEVERAGED = ["SSO", "QLD", "UPRO", "TQQQ", "UWM", "ROM", "UYG", "SPXL", "TNA", "SOXL"]
NEW_ETFS = [s for v in CATEGORIES.values() for s in v]
OLD_ETFS = list(audit.ETFS)
POST = "2014-12-31"
PLACEBO_P = 0.05
MIN_T_5BPS = 2.0


def cmd_fetch(a):
    have = 0
    for sym in NEW_ETFS + LEVERAGED + OLD_ETFS:
        if daily.load(sym) is not None and not a.refresh:
            have += 1
            continue
        try:
            daily.save(sym, daily.parse_daily(daily.fetch_daily(sym)))
            have += 1
        except daily.LabError as e:
            print("  %s: %s" % (sym, e))
        time.sleep(daily.PAUSE)
    print("%d symbols stored in %s" % (have, daily.STORE))
    return 0


def load(symbols):
    out = {}
    for s in symbols:
        D = daily.load(s)
        if D and len(D["c"]) > 260:
            out[s] = D
    return out


def r3_trades(uni):
    tb = {}
    for sym, D in uni.items():
        sig, ex = audit.rules(D, "wilder")["r3"]
        tb[sym] = audit.simulate(D, sig, ex, fill="open", max_days=30)
    return tb


def period_stats(by_day, dates, start):
    x = [statistics.mean(by_day[d]) if d in by_day else 0.0 for d in dates if d > start]
    return daily.stats(x)


def evaluate(uni, tb, reps, cost=2.0, seed=11):
    """-> {period: {"t", "mean", "p", "pl_median", "t5", "t10", "t20"}} for full and post-2014."""
    dates = sorted({d for D in uni.values() for d in D["d"]})
    starts = {"full": "0000", "post2014": POST}
    real = {k: period_stats(audit.daily_series(tb, uni, cost), dates, s) for k, s in starts.items()}
    pl = {k: [] for k in starts}
    rnd = random.Random(seed)
    for _ in range(reps):
        fake = {}
        for sym, trades in tb.items():
            D = uni[sym]
            n = len(D["c"])
            f = []
            for tr in trades:
                L = tr[1] - tr[0]
                s2 = rnd.randrange(200, n - L - 1)
                f.append((s2, s2 + L, 0.0, D["o"][s2 + 1]))
            fake[sym] = f
        ser = audit.daily_series(fake, uni, cost)
        for k, s in starts.items():
            pl[k].append(period_stats(ser, dates, s)["t"])
    out = {}
    for k, s in starts.items():
        ts = sorted(pl[k]) or [0.0]
        row = {"t": real[k]["t"], "mean": real[k]["mean"], "pl_median": ts[len(ts) // 2],
               "p": (1 + sum(1 for t in ts if t >= real[k]["t"])) / float(len(ts) + 1)}
        for c in (5.0, 10.0, 20.0):
            row["t%d" % c] = period_stats(audit.daily_series(tb, uni, c), dates, s)["t"]
        out[k] = row
    return out


def trade_summary(uni, tb):
    rets = [tr[2] * 1e4 for v in tb.values() for tr in v]
    if not rets:
        return "0 trades"
    return "%d trades in %d funds, avg %.0f bp gross, win %.0f%%" % (
        len(rets), sum(1 for v in tb.values() if v), statistics.mean(rets),
        100.0 * sum(1 for r in rets if r > 0) / len(rets))


def line(name, ev):
    f, p = ev["full"], ev["post2014"]
    return ("%-12s full t %5.2f (placebo med %5.2f, p %.3f, t@5bp %5.2f) | post-2014 t %5.2f "
            "(placebo med %5.2f, p %.3f, t@5bp %5.2f, t@20bp %5.2f)" % (
                name, f["t"], f["pl_median"], f["p"], f["t5"], p["t"], p["pl_median"], p["p"], p["t5"],
                p["t20"]))


def cmd_test(a):
    reps = a.placebos
    groups = [("NEW_ETFS", NEW_ETFS)] + list(CATEGORIES.items()) + [
        ("old 19 ETFs", OLD_ETFS), ("leveraged", LEVERAGED)]
    res = {}
    for name, syms in groups:
        uni = load(syms)
        if not uni:
            print("%-12s no data (run fetch)" % name)
            continue
        tb = r3_trades(uni)
        ev = evaluate(uni, tb, reps if name == "NEW_ETFS" else max(200, reps // 5))
        res[name] = ev
        print(line(name, ev))
        print("             %s; missing: %s" % (trade_summary(uni, tb),
                                                 ",".join(s for s in syms if s not in uni) or "none"))
    new = res.get("NEW_ETFS")
    if not new:
        return 1
    cats_beat = sum(1 for c in CATEGORIES if c in res and res[c]["post2014"]["t"] > res[c]["post2014"]["pl_median"])
    gates = {
        "placebo p < 0.05, full": new["full"]["p"] < PLACEBO_P,
        "placebo p < 0.05, post-2014": new["post2014"]["p"] < PLACEBO_P,
        "t >= 2 at 5 bps, full": new["full"]["t5"] >= MIN_T_5BPS,
        "t >= 2 at 5 bps, post-2014": new["post2014"]["t5"] >= MIN_T_5BPS,
        "beats placebo median in >= 3 of 5 categories (post-2014): %d" % cats_beat: cats_beat >= 3,
    }
    print("\nPre-registered gates on NEW_ETFS (%d placebos):" % reps)
    for g, ok in gates.items():
        print("  %-4s %s" % ("PASS" if ok else "FAIL", g))
    print("VERDICT: %s" % ("R3 PASSES on fresh ETFs" if all(gates.values()) else "R3 FAILS on fresh ETFs"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch")
    p.add_argument("--refresh", action="store_true")
    p = sub.add_parser("test")
    p.add_argument("--placebos", type=int, default=1000)
    a = ap.parse_args(argv)
    return {"fetch": cmd_fetch, "test": cmd_test}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
