#!/usr/bin/env python3
"""Pre-FOMC drift on the S&P 500 (research plan B4), pre-registered.

    python3 fomc.py fetch          # Fed meeting calendar (federalreserve.gov) + SPY and ^IRX from Yahoo
    python3 fomc.py run [--write]  # score -> results/fomc.json

Source: Lucca & Moench (2015, Journal of Finance 70(1)) "The Pre-FOMC Announcement Drift": from 1994 to 2011
the S&P 500 rose on average about 49 bps in the 24 hours before scheduled FOMC announcements, a large share of
the equity premium earned on 8 days a year. Later work reports it faded after the paper. This is the control
the research plan calls for.

PRE-REGISTERED 2026-11-24, committed before any return was computed. Not to be changed:
  * Events: scheduled FOMC meetings from February 1994 (statements began then) to today, from the Fed's own
    pages (fomchistoricalYYYY.htm through 2020, fomccalendars.htm from 2021). The announcement day is the
    meeting's last day. Conference calls, notation votes, unscheduled and cancelled meetings are excluded.
    An announcement day that isn't a SPY trading day is dropped.
  * H1 (primary): SPY close of the day before to the close of the announcement day (dividend-adjusted), minus
    that day's T-bill (^IRX / 100 / 252) and 2 bps round-trip cost; one observation per event.
  * H2: the pre-announcement part alone, SPY close of the day before to the announcement day's open
    (split-adjusted), minus 2 bps.
  * Split: in-sample = events 1994-2011 (the paper's sample); judged = events from 2012 on.
  * Verdict per hypothesis: PASS only if judged t >= 3 (the lab's bar) and in-sample t > 0.
  * Placebo: for each draw, the same number of random non-event SPY days in each year, 1,000 draws; reported
    as the share of draws whose judged mean beats the real one. 5 bps costs reported too.
  * Also reported: mean excess return on every other day, for scale.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import random
import re
import statistics
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402

STORE = os.path.join(HERE, "data", "fomc")
RESULTS = os.path.join(HERE, "results")
FED = "https://www.federalreserve.gov/monetarypolicy/"
FIRST_YEAR, LAST_HISTORICAL = 1994, 2020
COST_BPS, REF_COST_BPS = 2.0, 5.0
SPLIT_YEAR = 2012
T_BAR = 3.0
PLACEBO_DRAWS = 1000
FREEZE = "2026-11-24"   # H2 passed on this date; events after it are the forward test (added after the result)
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                          "august", "september", "october", "november", "december"])}
ABBR = {k[:3]: v for k, v in MONTHS.items()}
EXCLUDE = ("conference call", "notation vote", "unscheduled", "cancelled")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; day-trader-skill)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def last_day(month_text, day_text, year):
    """'Apr/May', '30-1' -> date(year, 5, 1); 'January 31-February 1' style handled via the last month named."""
    names = re.findall(r"[A-Za-z]+", month_text)
    mons = [MONTHS.get(n.lower()) or ABBR.get(n.lower()[:3]) for n in names]
    mons = [m for m in mons if m]
    days = [int(x) for x in re.findall(r"\d+", day_text)]
    if not mons or not days:
        return None
    return datetime.date(year, mons[-1], days[-1])


def parse_historical(html, year):
    out = []
    for h in re.findall(r"<h5[^>]*>(.*?)</h5>", html, re.S):
        t = clean(h)
        low = t.lower()
        if "meeting" not in low or any(x in low for x in EXCLUDE):
            continue
        head = t.split("Meeting")[0]
        d = last_day(head, re.sub(r"[A-Za-z]+", " ", head), year)
        if d:
            out.append(d)
    return out


def parse_current(html):
    out = []
    parts = re.split(r"(\d{4}) FOMC Meetings", html)
    for i in range(1, len(parts) - 1, 2):
        year, body = int(parts[i]), parts[i + 1]
        for mo, dt in re.findall(r'fomc-meeting__month[^>]*>(.*?)</div>\s*<div class="fomc-meeting__date[^>]*>(.*?)</div>',
                                 body, re.S):
            mo, dt = clean(mo), clean(dt)
            if any(x in (mo + " " + dt).lower() for x in EXCLUDE):
                continue
            d = last_day(mo, dt, year)
            if d:
                out.append(d)
    return out


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    dates = []
    for y in range(FIRST_YEAR, LAST_HISTORICAL + 1):
        dates += parse_historical(get(FED + "fomchistorical%d.htm" % y), y)
        time.sleep(0.5)
    dates += [d for d in parse_current(get(FED + "fomccalendars.htm")) if d.year > LAST_HISTORICAL]
    upcoming = sorted(set(d for d in dates if d > datetime.date.today()))
    dates = sorted(set(d for d in dates if d <= datetime.date.today()))
    with open(os.path.join(STORE, "events.json"), "w") as fh:
        json.dump([d.isoformat() for d in dates], fh)
    with open(os.path.join(STORE, "upcoming.json"), "w") as fh:
        json.dump([d.isoformat() for d in upcoming], fh)
    for sym in ("SPY", "^IRX"):
        b = daily.parse_daily(daily.fetch_daily(sym))
        with gzip.open(os.path.join(STORE, sym.replace("^", "_") + ".json.gz"), "wt") as fh:
            json.dump(b, fh)
    per_year = {}
    for d in dates:
        per_year[d.year] = per_year.get(d.year, 0) + 1
    print("events: %d (%s to %s); per year: %s" % (len(dates), dates[0], dates[-1],
                                                   ", ".join("%d:%d" % kv for kv in sorted(per_year.items()))))
    return 0


def load():
    with open(os.path.join(STORE, "events.json")) as fh:
        ev = json.load(fh)
    bars = {}
    for sym in ("SPY", "_IRX"):
        with gzip.open(os.path.join(STORE, sym + ".json.gz"), "rt") as fh:
            bars[sym] = json.load(fh)
    return ev, bars


def day_returns(bars):
    """{date: (close-to-close excess, close-to-open)} for SPY."""
    s, r = bars["SPY"], bars["_IRX"]
    rf = dict(zip(r["d"], r["c"]))
    last_rf, out = 0.0, {}
    for i in range(1, len(s["d"])):
        d = s["d"][i]
        last_rf = rf.get(d, last_rf)
        cc = s["a"][i] / s["a"][i - 1] - 1.0 - last_rf / 100.0 / 252.0
        co = s["o"][i] / s["c"][i - 1] - 1.0 if s["o"][i] else None
        out[d] = (cc, co)
    return out


def tstat(x):
    if len(x) < 3 or statistics.stdev(x) == 0:
        return 0.0
    return statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x)))


def stats(x):
    return {"n": len(x), "mean_bps": 1e4 * statistics.mean(x) if x else 0.0, "t": tstat(x)}


def score(days, events, k, cost):
    ins = [days[d][k] - cost / 1e4 for d in events if int(d[:4]) < SPLIT_YEAR and days[d][k] is not None]
    jud = [days[d][k] - cost / 1e4 for d in events if int(d[:4]) >= SPLIT_YEAR and days[d][k] is not None]
    return {"in_sample": stats(ins), "judged": stats(jud)}


def cmd_run(a):
    ev, bars = load()
    days = day_returns(bars)
    events = [d for d in ev if d in days]
    out = {"events_listed": len(ev), "events_scored": len(events), "dropped_not_trading_days": sorted(set(ev) - set(days)),
           "first": events[0], "last": events[-1]}
    for cost in (COST_BPS, REF_COST_BPS):
        out["cost_%g" % cost] = {"H1_close_to_close": score(days, events, 0, cost),
                                 "H2_close_to_open": score(days, events, 1, cost)}
    evset = set(events)
    others = [v[0] for d, v in days.items() if d not in evset and d >= "1994-02-01"]
    out["other_days_mean_bps"] = 1e4 * statistics.mean(others)
    by_year = {}
    for d in days:
        if d >= "1994-02-01" and d not in evset:
            by_year.setdefault(d[:4], []).append(d)
    count = {}
    for d in events:
        if int(d[:4]) >= SPLIT_YEAR:
            count[d[:4]] = count.get(d[:4], 0) + 1
    real = {k: out["cost_%g" % COST_BPS][key]["judged"]["mean_bps"]
            for k, key in (("H1", "H1_close_to_close"), ("H2", "H2_close_to_open"))}
    rng, beat = random.Random(7), {"H1": 0, "H2": 0}
    for _ in range(PLACEBO_DRAWS):
        pick = [d for y, n in count.items() for d in rng.sample(by_year[y], n)]
        for k, idx in (("H1", 0), ("H2", 1)):
            vals = [days[d][idx] - COST_BPS / 1e4 for d in pick if days[d][idx] is not None]
            if 1e4 * statistics.mean(vals) >= real[k]:
                beat[k] += 1
    out["placebo_p"] = {k: v / PLACEBO_DRAWS for k, v in beat.items()}
    fwd = [days[d][1] - COST_BPS / 1e4 for d in events if d > FREEZE and days[d][1] is not None]
    out["forward_H2"] = {"freeze": FREEZE, **stats(fwd)}
    up = os.path.join(STORE, "upcoming.json")
    if os.path.exists(up):
        with open(up) as fh:
            nxt = json.load(fh)
        out["next_event"] = nxt[0] if nxt else None
    out["verdict"] = {}
    for k, key in (("H1", "H1_close_to_close"), ("H2", "H2_close_to_open")):
        s = out["cost_%g" % COST_BPS][key]
        out["verdict"][k] = "PASS" if (s["judged"]["t"] >= T_BAR and s["in_sample"]["t"] > 0) else "FAIL"
        print("%s %-18s 1994-2011 %3d events %+6.1f bp t %+5.2f | 2012 on %3d events %+6.1f bp t %+5.2f | "
              "placebo p %.3f -> %s" % (k, key, s["in_sample"]["n"], s["in_sample"]["mean_bps"], s["in_sample"]["t"],
                                       s["judged"]["n"], s["judged"]["mean_bps"], s["judged"]["t"],
                                       out["placebo_p"][k], out["verdict"][k]))
    print("events %d scored of %d listed (%s to %s); other days average %+.1f bp" % (
        len(events), len(ev), events[0], events[-1], out["other_days_mean_bps"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "fomc.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return cmd_fetch(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
