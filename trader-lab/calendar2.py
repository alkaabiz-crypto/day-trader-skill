#!/usr/bin/env python3
"""Three calendar effects on SPY, each backtested on a $500 account. Pre-registered.

    python3 calendar2.py run [--write]   # needs fomc.py fetch (Fed calendar, SPY, ^IRX) -> results/calendar2.json

PRE-REGISTERED 2026-11-24, committed before any of these returns was computed. Not to be changed:
  Data: SPY dividend-adjusted closes and ^IRX from fomc.py's store; scheduled FOMC announcement days from fomc.py.
  Each rule holds SPY on its days (close to close) and T-bills on all others; 1 bp is paid on each switch in or out
  (2 bps a round trip). Statistics use SPY's return minus the T-bill on the days held.
  H1 FOMC cycle (Cieslak, Morse & Vissing-Jorgensen 2019, JF 74(5)): trading days are counted from the latest
     scheduled FOMC announcement (day 0); the day before an announcement is day -1. "Even weeks" are days -1 to 3,
     9 to 13, 19 to 23 and 29 to 33. Hold SPY on even-week days. In-sample 1994-2016 (the paper's sample), judged
     2017 on. Statistic: daily excess return on even-week days.
  H2 Pre-holiday (Ariel 1990, JF 45(5)): hold SPY on the last trading day before each NYSE holiday. A holiday is a
     weekday with no SPY trading, except the unscheduled closures 2001-09-11 to 09-14, 2004-06-11, 2007-01-02,
     2012-10-29/30, 2018-12-05 and 2025-01-09. In-sample before 2010, judged 2010 on. One observation per holiday.
  H3 Options-expiration week (the third Friday of the month, or the trading day before it if the market is
     closed): hold SPY from the close of the trading day before that week starts to the close on expiration day.
     In-sample before 2010, judged 2010 on. One observation per month.
  Verdict per hypothesis: PASS only if judged t >= 3 and in-sample t > 0.
  Reported: what $500 became (judged period and all years) next to $500 in SPY bought and held.
Research, not financial advice.
"""

import argparse
import datetime
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paper500 as p5  # noqa: E402

RESULTS = os.path.join(HERE, "results")
EVEN = set([-1, 0, 1, 2, 3]) | set(range(9, 14)) | set(range(19, 24)) | set(range(29, 34))
UNSCHEDULED = {"2001-09-11", "2001-09-12", "2001-09-13", "2001-09-14", "2004-06-11", "2007-01-02", "2012-10-29",
               "2012-10-30", "2018-12-05", "2025-01-09"}
SPLITS = {"H1": "2017-01-01", "H2": "2010-01-01", "H3": "2010-01-01"}
SWITCH_BPS = 1.0
T_BAR = 3.0


def fomc_days(dates, events):
    """{date: cycle day} for each trading date after the first FOMC event."""
    idx = {d: i for i, d in enumerate(dates)}
    ev = sorted(idx[e] for e in events if e in idx)
    out = {}
    for i, d in enumerate(dates):
        prev = [e for e in ev if e <= i]
        nxt = [e for e in ev if e > i]
        if nxt and nxt[0] - i == 1:
            out[d] = -1
        elif prev:
            out[d] = i - prev[-1]
    return out


def holidays(dates):
    """Weekdays between the first and last trading date with no trading, minus the unscheduled closures."""
    have = set(dates)
    d = datetime.date.fromisoformat(dates[0])
    end = datetime.date.fromisoformat(dates[-1])
    out = []
    while d <= end:
        s = d.isoformat()
        if d.weekday() < 5 and s not in have and s not in UNSCHEDULED:
            out.append(s)
        d += datetime.timedelta(days=1)
    return out


def pre_holiday_days(dates):
    import bisect
    out = set()
    for h in holidays(dates):
        i = bisect.bisect_left(dates, h) - 1
        if i >= 0:
            out.add(dates[i])
    return out


def opex_weeks(dates):
    """{expiration date: [dates held]}: from the day after the prior week's last trading day to expiration."""
    import bisect
    have = set(dates)
    out = {}
    y0, y1 = int(dates[0][:4]), int(dates[-1][:4])
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            d = datetime.date(y, m, 1)
            fridays = [d + datetime.timedelta(days=k) for k in range(31)
                       if (d + datetime.timedelta(days=k)).month == m and (d + datetime.timedelta(days=k)).weekday() == 4]
            if len(fridays) < 3:
                continue
            ex = fridays[2]
            while ex.isoformat() not in have and ex.isoformat() >= dates[0]:
                ex -= datetime.timedelta(days=1)
            exs = ex.isoformat()
            if exs not in have:
                continue
            monday = (fridays[2] - datetime.timedelta(days=4)).isoformat()
            i0 = bisect.bisect_left(dates, monday)
            i1 = dates.index(exs)
            if i0 <= i1:
                out[exs] = dates[i0:i1 + 1]
    return out


def strategy(dates, ret, rf, held):
    """Daily value path of $500 holding SPY on `held` days, T-bills otherwise, 1 bp per switch."""
    value, path, prev_in = p5.START, [], False
    for d in dates[1:]:
        inn = d in held
        r = ret[d] if inn else rf.get(d, 0.0)
        if inn != prev_in:
            r -= SWITCH_BPS / 1e4
        value *= 1 + r
        path.append((d, value))
        prev_in = inn
    return path


def stats(obs, split):
    a = [v for d, v in obs if d < split]
    b = [v for d, v in obs if d >= split]
    f = lambda x: {"n": len(x), "mean_bps": 1e4 * statistics.mean(x) if x else 0.0, "t": p5.tstat(x)}  # noqa: E731
    return {"in_sample": f(a), "judged": f(b)}


def cmd_run(a):
    import fomc
    ev, bars = fomc.load()
    spy = bars["SPY"]
    dates = [d for d in spy["d"] if d >= "1994-01-01"]
    adj = dict(zip(spy["d"], spy["a"]))
    allp = spy["d"]
    ret = {}
    for i in range(1, len(allp)):
        ret[allp[i]] = adj[allp[i]] / adj[allp[i - 1]] - 1.0
    rf = p5.rf_daily()
    ex = {d: ret[d] - rf.get(d, 0.0) for d in dates if d in ret}
    cyc = fomc_days(dates, ev)
    held = {
        "H1": {d for d, k in cyc.items() if k in EVEN},
        "H2": pre_holiday_days(dates),
        "H3": {d for w in opex_weeks(dates).values() for d in w},
    }
    obs = {
        "H1": [(d, ex[d]) for d in sorted(held["H1"]) if d in ex],
        "H2": [(d, ex[d] - 2 * SWITCH_BPS / 1e4) for d in sorted(held["H2"]) if d in ex],
        "H3": [(k, sum(ex.get(d, 0.0) for d in w) - 2 * SWITCH_BPS / 1e4) for k, w in sorted(opex_weeks(dates).items())],
    }
    bh = [(d, 0.0) for d in dates]
    bh_path, v = [], p5.START
    for d in dates[1:]:
        v *= 1 + ret[d]
        bh_path.append((d, v))
    out = {"first": dates[0], "last": dates[-1], "results": {}}
    names = {"H1": "FOMC cycle, even weeks", "H2": "Day before a holiday", "H3": "Options-expiration week"}
    for k in ("H1", "H2", "H3"):
        s = stats(obs[k], SPLITS[k])
        s["days_in_market_share"] = round(len(held[k]) / len(dates), 3)
        path = strategy(dates, ret, rf, held[k])
        s["usd_judged"] = p5.dollars(path, SPLITS[k])
        s["usd_all"] = p5.dollars(path)
        s["spy_usd_judged"] = p5.dollars(bh_path, SPLITS[k])
        s["spy_usd_all"] = p5.dollars(bh_path)
        s["verdict"] = "PASS" if (s["judged"]["t"] >= T_BAR and s["in_sample"]["t"] > 0) else "FAIL"
        s["name"] = names[k]
        out["results"][k] = s
        print("%s %-26s IS n %4d %+6.1f bp t %+5.2f | judged n %4d %+6.1f bp t %+5.2f | $500 -> $%.0f since %s "
              "(SPY $%.0f) -> %s" % (k, names[k], s["in_sample"]["n"], s["in_sample"]["mean_bps"], s["in_sample"]["t"],
                                     s["judged"]["n"], s["judged"]["mean_bps"], s["judged"]["t"], s["usd_judged"],
                                     SPLITS[k][:4], s["spy_usd_judged"], s["verdict"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "calendar2.json"))
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
