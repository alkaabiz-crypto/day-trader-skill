#!/usr/bin/env python3
"""News as a tested signal: do stocks keep drifting the way they jumped on earnings news?

    python3 news_events.py fetch      # SEC earnings 8-K dates + Yahoo daily closes (needs SEC_USER_AGENT)
    python3 news_events.py test [--write]

Why: headlines have no free history, so the news skill could never be backtested. Earnings releases can:
companies file them with the SEC as 8-K item 2.02, time-stamped, back to the early 2000s. Post-earnings
announcement drift (Ball & Brown 1968; Bernard & Thomas 1989) is the most replicated news anomaly: after a
big earnings surprise, prices keep moving the same way for weeks. Later work reports it shrank as markets
got faster (Chordia et al. 2009; Martineau 2022), so this tests whether it is still there for the lab's names.

PRE-REGISTERED 2026-11-24, before any SEC or price data was fetched. Not to be changed after the first run:

  Stocks: the 30 single stocks in lab.UNIVERSE (ETFs file no earnings). Today's names, so survivor-biased;
    stated up front. Foreign filers (SHOP, ARM) report on 6-K, not 8-K, so they may contribute no events.
  Events: every 8-K whose items include 2.02, from the company's full SEC submissions history. Reaction day
    = the first trading day whose close comes after the filing's acceptance time (New York): a filing after
    16:00 or on a non-trading day reacts the next session. Reaction = that close / the previous close - 1.
  Rule: if |reaction| >= k%, take the reaction's side (long after a jump up, short after a drop; variant
    long-only), enter at the NEXT day's close, hold H trading days, exit at that close.
    Grid: k in {2, 4}, H in {5, 20, 60}, sides in {both, long} = 12 variants, chosen on IS only.
  Score: each trade's return minus the same-window equal-weight return of all 30 stocks (so market moves
    don't count), minus costs of 10 bps per round trip (re-run at 20 bps).
  Periods (by entry date): IS 2006-2014, OOS 2015-2020, HOLDOUT 2021 on.
  Statistics: trades in the same calendar month are averaged first; t is over months (overlapping holds
    are correlated, so a t over single trades would overstate).
  PASS needs all of: IS t >= 2; OOS mean > 0 and HOLDOUT mean > 0; post-IS t >= 3 at 10 AND 20 bps; and a
    placebo: the same rule applied to big moves on days with NO earnings filing within 5 trading days (same
    stocks, same k), drawn to the same number of trades 1,000 times, beats the real post-IS mean < 5% of the
    time (if earnings news adds nothing beyond "big move", there is no news edge).
Contact: SEC requires a User-Agent with a contact address; it is read from SEC_USER_AGENT (or the
  sec_user_agent in trader/config.json, the news skill's setting) and never printed or stored here.
Research, not financial advice.
"""

import argparse
import bisect
import datetime
import gzip
import json
import math
import os
import random
import statistics
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import alloc  # noqa: E402  (adjusted-close parsing)
import audit  # noqa: E402  (ETF list, to exclude)
import daily  # noqa: E402  (Yahoo fetch)
import lab  # noqa: E402  (universe)

STORE = os.path.join(HERE, "data", "news_events")
RESULTS = os.path.join(HERE, "results")
IS_END, OOS_END, START = "2014-12-31", "2020-12-31", "2006-01-01"
GRID = [{"k": k, "h": h, "sides": s} for k in (2.0, 4.0) for h in (5, 20, 60) for s in ("both", "long")]
COSTS = (10.0, 20.0)
PLACEBO_REPS = 1000
NO_NEWS_GAP = 5


def stocks():
    etfs = set(audit.ETFS) | {"SPY", "QQQ", "IWM", "DIA", "SMH", "XLF", "XLK", "XLE", "TLT", "GLD"}
    return [s for s in lab.UNIVERSE if s not in etfs]


def user_agent():
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        p = os.path.join(ROOT, "trader", "config.json")
        if os.path.exists(p):
            with open(p) as fh:
                ua = str(json.load(fh).get("sec_user_agent") or "").strip()
    if "@" not in ua:
        raise daily.LabError("SEC needs a contact address: set SEC_USER_AGENT in the environment settings")
    return ua


def sec_get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def ny_from_sec(ts):
    """SEC acceptanceDateTime ('2019-10-30T16:31:05.000Z', actually Eastern wall time) -> naive NY datetime."""
    return datetime.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")


def cmd_fetch(a):
    ua = user_agent()
    os.makedirs(STORE, exist_ok=True)
    tick = sec_get("https://www.sec.gov/files/company_tickers.json", ua)
    cik = {v["ticker"].upper(): "%010d" % int(v["cik_str"]) for v in tick.values()}
    events = {}
    for s in stocks():
        if s not in cik:
            print("%-5s no CIK" % s)
            continue
        sub = sec_get("https://data.sec.gov/submissions/CIK%s.json" % cik[s], ua)
        blocks = [sub["filings"]["recent"]]
        for f in sub["filings"].get("files", []):
            time.sleep(0.15)
            blocks.append(sec_get("https://data.sec.gov/submissions/%s" % f["name"], ua))
        ev = set()
        for b in blocks:
            for form, items, acc in zip(b["form"], b.get("items", [""] * len(b["form"])), b["acceptanceDateTime"]):
                if form.startswith("8-K") and "2.02" in str(items):
                    ev.add(acc[:19])
        events[s] = sorted(ev)
        D = alloc.parse_adj(daily.fetch_daily(s))
        with gzip.open(os.path.join(STORE, "%s.json.gz" % s), "wt") as fh:
            json.dump(D, fh)
        print("%-5s %3d earnings 8-Ks, %d days of prices from %s" % (s, len(events[s]), len(D["d"]), D["d"][0]), flush=True)
        time.sleep(0.2)
    with open(os.path.join(STORE, "events.json"), "w") as fh:
        json.dump(events, fh, indent=0)
    return 0


def load():
    with open(os.path.join(STORE, "events.json")) as fh:
        events = json.load(fh)
    px = {}
    for s in events:
        p = os.path.join(STORE, "%s.json.gz" % s)
        if os.path.exists(p):
            with gzip.open(p, "rt") as fh:
                D = json.load(fh)
            px[s] = (D["d"], D["c"])
    return events, px


def reaction_index(dates, acc):
    """Index of the first trading day whose 16:00 close comes after the acceptance time."""
    t = ny_from_sec(acc)
    day = t.date().isoformat()
    k = bisect.bisect_left(dates, day)
    if k < len(dates) and dates[k] == day and t.time() < datetime.time(16, 0):
        return k
    return bisect.bisect_right(dates, day)


def bench(px, d0, d1):
    """Equal-weight return of all stocks with prices on both dates."""
    rs = []
    for ds, cs in px.values():
        i, j = bisect.bisect_left(ds, d0), bisect.bisect_left(ds, d1)
        if i < len(ds) and j < len(ds) and ds[i] == d0 and ds[j] == d1:
            rs.append(cs[j] / cs[i] - 1)
    return statistics.mean(rs) if rs else None


def trades_for(px, s, idx_list, p, cost):
    ds, cs = px[s]
    out = []
    for r in idx_list:
        if r < 1 or r + 1 + p["h"] >= len(ds):
            continue
        move = cs[r] / cs[r - 1] - 1
        if abs(move) * 100 < p["k"]:
            continue
        side = 1 if move > 0 else -1
        if p["sides"] == "long" and side < 0:
            continue
        e, x = r + 1, r + 1 + p["h"]
        b = bench(px, ds[e], ds[x])
        if b is None:
            continue
        ret = side * ((cs[x] / cs[e] - 1) - b) - cost / 1e4
        out.append((ds[e], ret))
    return out


def month_t(trades):
    by = {}
    for d, r in trades:
        by.setdefault(d[:7], []).append(r)
    xs = [statistics.mean(v) for v in by.values()]
    if len(xs) < 6 or statistics.pstdev(xs) == 0:
        return 0.0, (statistics.mean(xs) if xs else 0.0), len(trades)
    return statistics.mean(xs) / (statistics.stdev(xs) / math.sqrt(len(xs))), statistics.mean(xs), len(trades)


def split(trades):
    return ([t for t in trades if START <= t[0] <= IS_END], [t for t in trades if IS_END < t[0] <= OOS_END],
            [t for t in trades if t[0] > OOS_END], [t for t in trades if t[0] > IS_END])


def event_indexes(events, px):
    ev, no = {}, {}
    for s, accs in events.items():
        if s not in px:
            continue
        ds = px[s][0]
        idx = sorted({reaction_index(ds, a) for a in accs if a[:10] >= "2005-06-01"})
        ev[s] = [i for i in idx if i < len(ds)]
        near = set()
        for i in ev[s]:
            near.update(range(i - NO_NEWS_GAP, i + NO_NEWS_GAP + 1))
        no[s] = [i for i in range(1, len(ds)) if i not in near and ds[i] >= START]
    return ev, no


def cmd_test(a):
    events, px = load()
    ev, no = event_indexes(events, px)
    print("News events: %d stocks, %d earnings reactions" % (len(ev), sum(len(v) for v in ev.values())))
    best = None
    for p in GRID:
        tr = [t for s in ev for t in trades_for(px, s, ev[s], p, COSTS[0])]
        t_is = month_t(split(tr)[0])
        if best is None or t_is[0] > best[1][0]:
            best = (p, t_is)
    p, t_is = best
    print("Chosen on IS: %s  IS t %.2f (%d trades, %.1f bp/month)" % (json.dumps(p), t_is[0], t_is[2], 1e4 * t_is[1]))
    rep = {"params": p, "is": t_is}
    ok = True
    for cost in COSTS:
        tr = [t for s in ev for t in trades_for(px, s, ev[s], p, cost)]
        is_, oos, ho, post = split(tr)
        r = {n: month_t(x) for n, x in (("is", is_), ("oos", oos), ("ho", ho), ("post", post))}
        ctrl = [t for s in no for t in trades_for(px, s, no[s], p, cost) if t[0] > IS_END]
        rnd = random.Random(31)
        real = statistics.mean([x for _, x in post]) if post else 0.0
        hits = 0
        for _ in range(PLACEBO_REPS):
            samp = rnd.sample(ctrl, min(len(post), len(ctrl))) if ctrl else []
            hits += bool(samp) and statistics.mean([x for _, x in samp]) >= real
        r["placebo_p"] = hits / PLACEBO_REPS if ctrl else float("nan")
        r["control_post_mean_bp"] = 1e4 * statistics.mean([x for _, x in ctrl]) if ctrl else float("nan")
        ok = ok and (r["is"][0] >= 2 and r["oos"][1] > 0 and r["ho"][1] > 0 and r["post"][0] >= 3
                     and r["placebo_p"] < 0.05)
        rep["cost_%d" % cost] = r
        print("@%2.0fbp  IS t %5.2f | OOS %4d tr %6.1f bp | HOLD %4d tr %6.1f bp | post-IS t %5.2f | big moves w/o "
              "earnings %6.1f bp, placebo p %.3f" % (cost, r["is"][0], r["oos"][2], 1e4 * r["oos"][1], r["ho"][2],
                                                     1e4 * r["ho"][1], r["post"][0], r["control_post_mean_bp"],
                                                     r["placebo_p"]))
    rep["verdict"] = "PASS" if ok else "FAIL"
    print("\nVerdict: %s. Research, not financial advice." % rep["verdict"])
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(rep, fh, indent=1, default=float)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    p = sub.add_parser("test")
    p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "news-events.json"))
    a = ap.parse_args(argv)
    try:
        return {"fetch": cmd_fetch, "test": cmd_test}[a.cmd](a) if a.cmd else ap.print_help() or 1
    except daily.LabError as e:
        print("news_events.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
