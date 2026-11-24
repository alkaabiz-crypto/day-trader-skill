#!/usr/bin/env python3
"""Crypto cross-sectional momentum (research plan B3), pre-registered.

    python3 crypto_xs.py fetch          # Yahoo daily bars for the fixed coin list -> data/crypto_xs (gitignored)
    python3 crypto_xs.py run [--write]  # score it -> results/crypto-xs.json

Source: Liu, Tsyvinski & Wu (2022, Journal of Finance 77(2)) "Common Risk Factors in Cryptocurrency":
coin returns over the past 1-4 weeks predict the next week's cross-section (momentum).

PRE-REGISTERED 2026-11-24, committed before any coin data was downloaded. Not to be changed:
  * Universe: the fixed COINS list below, written down from memory of the large coins of 2017-2022,
    dead ones included (LUNA, FTT, ...) to soften survivor bias. A ticker Yahoo doesn't serve is dropped
    mechanically, never for its returns. Survivor bias remains (coins that died before Yahoo listed
    them are missing), so a PASS would still need a survivorship audit before anyone trusts it.
  * Weeks: Sunday close to Sunday close (UTC daily closes).
  * Eligible in week w: a close on every day of the 3 formation weeks, and a median daily dollar volume
    over those 21 days of at least $1M. At least 9 eligible coins, else that week is skipped.
  * Signal: past 3-week return. Sort into terciles, equal-weight.
  * H1 (primary): long the top tercile, short the bottom, held 1 week. H2: long the top tercile minus the
    equal-weight return of all eligible coins (the long-only version an investor could hold).
  * A coin with no close at the end of the hold week is valued at its last close that week.
  * Costs: 25 bps per side on every unit of weight traded (sum |w_new - w_old| x 25 bps); 10 bps reported.
  * Split: in-sample = weeks ending before 2021-01-01; judged = weeks from 2021-01-01 on.
  * Verdict per hypothesis, at 25 bps: PASS only if judged t >= 3 (Harvey, Liu & Zhu bar, stricter than a
    Bonferroni bar over 2) and in-sample t > 0. Also reported: a placebo where the ranks are shuffled each
    week (1,000 draws), and the share of draws whose judged mean beats the real one.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import random
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402  (fetch_daily, parse_daily)

STORE = os.path.join(HERE, "data", "crypto_xs")
RESULTS = os.path.join(HERE, "results")
COINS = ["BTC", "ETH", "XRP", "LTC", "BCH", "ADA", "DOT", "LINK", "XLM", "DOGE", "BNB", "TRX", "EOS", "XMR",
         "ETC", "NEO", "DASH", "ZEC", "XTZ", "ATOM", "VET", "MIOTA", "WAVES", "QTUM", "OMG", "ZRX", "BAT",
         "ICX", "ONT", "XNO", "LSK", "SC", "DGB", "XEM", "STEEM", "BTG", "DCR", "REP", "ALGO", "SOL", "AVAX",
         "MATIC", "UNI7083", "AAVE", "FIL", "NEAR", "LUNA1", "FTT", "SHIB", "HBAR", "ICP", "SAND", "MANA",
         "AXS", "CRO", "EGLD", "THETA", "KSM", "CHZ", "GRT6719", "BSV", "XVG", "ARDR", "KMD", "STRAX",
         "WAN", "HOT", "ENJ", "MKR", "COMP", "SNX", "YFI", "SUSHI", "CRV", "CAKE", "RUNE", "KLAY", "CEL"]
FORM_WEEKS = 3
MIN_DOLLAR_VOL = 1e6
MIN_COINS = 9
COST_BPS = 25.0
REF_COST_BPS = 10.0
SPLIT = "2021-01-01"
T_BAR = 3.0
PLACEBO_DRAWS = 1000


def path(c):
    return os.path.join(STORE, "%s.json.gz" % c)


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    got, missing = 0, []
    for c in COINS:
        if os.path.exists(path(c)) and not a.full:
            got += 1
            continue
        try:
            bars = daily.parse_daily(daily.fetch_daily("%s-USD" % c))
        except Exception as e:  # noqa: BLE001  (a ticker Yahoo lacks is dropped mechanically)
            missing.append("%s (%s)" % (c, e))
            continue
        tmp = path(c) + ".tmp"
        with gzip.open(tmp, "wt") as fh:
            json.dump({"d": bars["d"], "c": bars["c"], "v": bars["v"]}, fh)
        os.replace(tmp, path(c))
        got += 1
        time.sleep(1.0)
    print("coins stored: %d of %d" % (got, len(COINS)))
    if missing:
        print("not served by Yahoo (dropped): " + "; ".join(missing))
    return 0


def load():
    out = {}
    for c in COINS:
        if os.path.exists(path(c)):
            with gzip.open(path(c), "rt") as fh:
                b = json.load(fh)
            out[c] = {d: (cl, v) for d, cl, v in zip(b["d"], b["c"], b["v"]) if cl and cl > 0}
    return out


def sundays(data):
    first = min(min(x) for x in data.values() if x)
    last = max(max(x) for x in data.values() if x)
    d = datetime.date.fromisoformat(first)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)
    end = datetime.date.fromisoformat(last)
    out = []
    while d <= end:
        out.append(d)
        d += datetime.timedelta(days=7)
    return out


def iso(d):
    return d.isoformat()


def eligible(px, t0):
    """Coin passes at formation end t0: a close every day of the 21 days ending t0, median $ vol >= 1M."""
    days = [iso(t0 - datetime.timedelta(days=k)) for k in range(7 * FORM_WEEKS + 1)]
    if any(d not in px for d in days):
        return None
    dv = sorted(px[d][0] * (px[d][1] or 0) for d in days[:-1])
    if dv[len(dv) // 2] < MIN_DOLLAR_VOL:
        return None
    return px[days[0]][0] / px[days[-1]][0] - 1.0


def hold_return(px, t0):
    """t0 close to the next Sunday's close, or the last close that week if the coin stops trading."""
    if iso(t0) not in px:
        return None
    end = None
    for k in range(7, 0, -1):
        d = iso(t0 + datetime.timedelta(days=k))
        if d in px:
            end = px[d][0]
            break
    return (end if end is not None else px[iso(t0)][0]) / px[iso(t0)][0] - 1.0


def weeks(data):
    """-> list of (week_end_date, {coin: signal}, {coin: next-week return})."""
    out = []
    last = max(max(x) for x in data.values() if x)
    for t0 in sundays(data):
        if iso(t0 + datetime.timedelta(days=7)) > last:
            break  # the hold week isn't over yet
        sig, ret = {}, {}
        for c, px in data.items():
            s = eligible(px, t0)
            if s is None:
                continue
            r = hold_return(px, t0)
            if r is None:
                continue
            sig[c], ret[c] = s, r
        if len(sig) >= MIN_COINS:
            out.append((t0 + datetime.timedelta(days=7), sig, ret))
    return out


def portfolios(sig):
    ranked = sorted(sig, key=lambda c: sig[c])
    n = len(ranked) // 3
    return ranked[-n:], ranked[:n], ranked


def series(wk, cost_bps, shuffle=None):
    """Weekly net returns for H1 (long-short) and H2 (top minus equal weight)."""
    h1, h2, dates = [], [], []
    prev1, prev2 = {}, {}
    for end, sig, ret in wk:
        s = sig
        if shuffle is not None:
            vals = list(sig.values())
            shuffle.shuffle(vals)
            s = dict(zip(sig.keys(), vals))
        top, bot, allc = portfolios(s)
        w1 = {c: 1.0 / len(top) for c in top}
        for c in bot:
            w1[c] = w1.get(c, 0.0) - 1.0 / len(bot)
        w2 = {c: 1.0 / len(top) for c in top}
        for c in allc:
            w2[c] = w2.get(c, 0.0) - 1.0 / len(allc)
        out = []
        for w, prev in ((w1, prev1), (w2, prev2)):
            turn = sum(abs(w.get(c, 0.0) - prev.get(c, 0.0)) for c in set(w) | set(prev))
            out.append(sum(w[c] * ret[c] for c in w) - turn * cost_bps / 1e4)
        prev1, prev2 = w1, w2
        h1.append(out[0])
        h2.append(out[1])
        dates.append(iso(end))
    return dates, h1, h2


def tstat(x):
    if len(x) < 3 or statistics.stdev(x) == 0:
        return 0.0
    return statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x)))


def split_stats(dates, x):
    a = [v for d, v in zip(dates, x) if d < SPLIT]
    b = [v for d, v in zip(dates, x) if d >= SPLIT]
    f = lambda s: {"weeks": len(s), "mean_pct_wk": 100 * statistics.mean(s) if s else 0.0, "t": tstat(s)}  # noqa: E731
    return {"in_sample": f(a), "judged": f(b)}


def cmd_run(a):
    data = load()
    if not data:
        print("no data: run `crypto_xs.py fetch` first")
        return 1
    wk = weeks(data)
    out = {"coins_with_data": len(data), "weeks": len(wk),
           "first": iso(wk[0][0]) if wk else None, "last": iso(wk[-1][0]) if wk else None,
           "avg_eligible": statistics.mean(len(s) for _, s, _ in wk) if wk else 0}
    for cost in (COST_BPS, REF_COST_BPS):
        dates, h1, h2 = series(wk, cost)
        out["cost_%g" % cost] = {"H1_long_short": split_stats(dates, h1), "H2_top_minus_market": split_stats(dates, h2)}
    dates, h1, h2 = series(wk, COST_BPS)
    real = {"H1": statistics.mean([v for d, v in zip(dates, h1) if d >= SPLIT]),
            "H2": statistics.mean([v for d, v in zip(dates, h2) if d >= SPLIT])}
    rng = random.Random(7)
    beat = {"H1": 0, "H2": 0}
    for _ in range(PLACEBO_DRAWS):
        d2, p1, p2 = series(wk, COST_BPS, shuffle=rng)
        for k, s in (("H1", p1), ("H2", p2)):
            if statistics.mean([v for d, v in zip(d2, s) if d >= SPLIT]) >= real[k]:
                beat[k] += 1
    out["placebo_p"] = {k: v / PLACEBO_DRAWS for k, v in beat.items()}
    verdict = {}
    for k, key in (("H1", "H1_long_short"), ("H2", "H2_top_minus_market")):
        s = out["cost_%g" % COST_BPS][key]
        verdict[k] = "PASS" if (s["judged"]["t"] >= T_BAR and s["in_sample"]["t"] > 0) else "FAIL"
    out["verdict"] = verdict
    for k, key in (("H1", "H1_long_short"), ("H2", "H2_top_minus_market")):
        s = out["cost_%g" % COST_BPS][key]
        print("%s %-22s IS %4d wk %+6.2f%%/wk t %+5.2f | judged %4d wk %+6.2f%%/wk t %+5.2f | placebo p %.3f -> %s" % (
            k, key, s["in_sample"]["weeks"], s["in_sample"]["mean_pct_wk"], s["in_sample"]["t"],
            s["judged"]["weeks"], s["judged"]["mean_pct_wk"], s["judged"]["t"], out["placebo_p"][k], verdict[k]))
    print("coins %d, weeks %d (%s to %s), avg eligible %.1f" % (
        out["coins_with_data"], out["weeks"], out["first"], out["last"], out["avg_eligible"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("--full", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "crypto-xs.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return cmd_fetch(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
