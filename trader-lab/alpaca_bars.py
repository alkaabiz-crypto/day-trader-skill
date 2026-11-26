#!/usr/bin/env python3
"""Years of whole-market 5-minute history from Alpaca (SIP tape), reduced on the fly for two uses:

    python3 alpaca_bars.py fetch [--from 2019-01] [--to 2026-11] [--top 500]
    python3 alpaca_bars.py stocks [--write]       # the stock bot's and the scanner track's rules, every day

1. Day summaries for the day-trading brain (daybrain/alpaca_days.DAY_FIELDS), saved to data/alpaca_days/ so
   `daybrain/brain.py study --store alpaca` reads them unchanged.
2. Per stock-day "bot records": what the live stock bot (bot.py stocks) and the 09:50 scanner track
   (paper.py scanner) would have seen at each decision time and what the trade would have made, using the
   same functions they use (paper.scanner_plan, paper.fill_long). Saved to data/alpaca5/<YYYY-MM>.json.gz.
   Raw bars are not kept (years of them for 500 names would be many gigabytes).
Keys: the environment's network secret for data.alpaca.markets; nothing is stored here.

STOCK BACKTEST, PRE-REGISTERED 2026-11-26 (the owner: "Alpaca works now, test what you couldn't"), before
any run. The rules are the bots' own, unchanged:
  Universe: today's 500 most-traded US stocks (data/wm5/_liquid.json; survivorship: today's names), each day
    only names with price >= $5 and a 60-day average volume >= 1M shares (bot_backtest.py's floor), from
    the trailing 60 sessions.
  Stock bot: decisions at 10:17, 11:17, 12:17, 13:17, 14:17. A candidate's latest completed 5-minute close
    is above the 9:30-9:45 range high, after a close above it. Rank by dollar volume so far, enter at the
    next bar's open, stop at the range midpoint, 2R target, out by 15:55. Costs from paper.scanner_plan
    (spread estimate + slippage + SEC fee). Two sizings:
      old  2 a run, 5 a day, $50 risk a day (the rule backtested on 59 days)
      now  10 a run, 50 a day, $500 risk a day (the live bot since 2026-11-24)
  Scanner track: 09:50, the best 3 by the live rule (the least extended over the range high), target 1R,
    same costs.
  Judged: per-trade net $ and daily t over 2019-2026, and each year separately. PASS (backtest only): daily
    t >= 3 over all years and positive in at least 6 of the 8 calendar years. Compared with $ in SPY.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "daybrain"))
import alpaca_days  # noqa: E402
import bot  # noqa: E402
import bot_data  # noqa: E402
import lab  # noqa: E402
import paper  # noqa: E402

STORE = os.path.join(HERE, "data", "alpaca5")
DECISIONS = ["10:17", "11:17", "12:17", "13:17", "14:17"]
SCAN_AT = "09:50"
RESULT = os.path.join(HERE, "results", "alpaca-stocks.json")
SIZINGS = {"old": (2, 5, 50.0), "now": (10, 50, 500.0)}


def to_sessions(bl):
    """Alpaca bars for one symbol -> {date: [78 bar dicts]} (complete regular sessions only)."""
    by = {}
    for b in bl:
        t = datetime.datetime.strptime(b["t"][:19], "%Y-%m-%dT%H:%M:%S")
        ny = lab.to_eastern(t)
        slot = (ny.hour * 60 + ny.minute - lab.OPEN_MIN) // 5
        if 0 <= slot < 78:
            by.setdefault(ny.date().isoformat(), {})[slot] = {"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                                                              "v": b["v"]}
    return {d: [s[i] for i in range(78)] for d, s in by.items() if all(i in s for i in range(78))}


def done_of(hhmm):
    return (int(hhmm[:2]) * 60 + int(hhmm[3:]) - lab.OPEN_MIN) // 5


def trade(bars, done, slot, oh, ol, cfg):
    px = bars[done - 1]["c"]
    p = paper.scanner_plan({"symbol": "X", "price": px, "or_high": oh, "or_low": ol}, bars[:done], set(), cfg)
    if not p:
        return None
    e, x, how = paper.fill_long(bars, slot, p["stop"], p["target"])
    notional = p["shares"] * e
    return [round(p["shares"] * (x - e) - notional * p["cost_bps"] / 1e4, 4), round(p["max_loss_usd"], 2), how]


def records(bars):
    """One stock-day -> compact record: close, volume, and per decision (cum $ volume, pct over, trade)."""
    oh = max(b["h"] for b in bars[:3])
    ol = min(b["l"] for b in bars[:3])
    first = next((k for k in range(3, 78) if bars[k]["c"] > oh), None)
    rec = {"c": bars[-1]["c"], "v": sum(b["v"] for b in bars), "d": {}}
    cv, run = [], 0.0
    for b in bars:
        run += b["c"] * b["v"]
        cv.append(run)
    bot_cfg = dict(paper.SCANNER_CFG, target_r=2.0)
    for hhmm in [SCAN_AT] + DECISIONS:
        done = done_of(hhmm)
        px = bars[done - 1]["c"]
        if first is None or first >= done or not px > oh:
            continue
        slot = done if hhmm == SCAN_AT else bot.next_slot(hhmm)
        t = trade(bars, done, slot, oh, ol, paper.SCANNER_CFG if hhmm == SCAN_AT else bot_cfg)
        if t:
            rec["d"][hhmm] = [round(cv[done - 1]), round(px / oh - 1, 5)] + t
    return rec


def fetch_month(month, symbols):
    y, m = map(int, month.split("-"))
    start = "%04d-%02d-01T00:00:00Z" % (y, m)
    end = "%04d-%02d-01T00:00:00Z" % ((y + 1, 1) if m == 12 else (y, m + 1))
    days, recs = {}, {}
    for i in range(0, len(symbols), alpaca_days.BATCH):
        batch = symbols[i:i + alpaca_days.BATCH]
        raw, token = {}, None
        while True:
            p = {"symbols": ",".join(batch), "timeframe": "5Min", "start": start, "end": end, "feed": "sip",
                 "adjustment": "all", "limit": 10000}
            if token:
                p["page_token"] = token
            doc = alpaca_days.get(p)
            for s, bl in (doc.get("bars") or {}).items():
                raw.setdefault(s, []).extend(bl)
            token = doc.get("next_page_token")
            time.sleep(0.32)
            if not token:
                break
        for s, bl in raw.items():
            sm = alpaca_days.summarise(bl)
            if sm:
                days[s] = sm
            sess = to_sessions(bl)
            if sess:
                recs[s] = {d: records(b) for d, b in sess.items()}
    return days, recs


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path + ".tmp", "wt") as fh:
        json.dump(obj, fh, separators=(",", ":"))
    os.replace(path + ".tmp", path)


def cmd_fetch(a):
    with open(os.path.join(bot_data.WM5, "_liquid.json")) as fh:
        syms = json.load(fh)[:a.top]
    for s in ("SPY", "QQQ", "IWM"):
        if s not in syms:
            syms.append(s)
    for month in alpaca_days.month_range(a.frm, a.to):
        p = os.path.join(STORE, month + ".json.gz")
        if os.path.exists(p):
            continue
        t0 = time.time()
        days, recs = fetch_month(month, syms)
        save(os.path.join(alpaca_days.STORE, month + ".json.gz"), days)
        save(p, recs)
        print("  %s: %d names, %d stock-days, %.0f s" % (month, len(recs), sum(len(v) for v in recs.values()),
                                                         time.time() - t0), flush=True)
    return 0


# ---------------------------------------------------------------- the backtest

def load_records():
    out = {}
    for f in sorted(os.listdir(STORE)):
        if f.endswith(".json.gz"):
            with gzip.open(os.path.join(STORE, f), "rt") as fh:
                for s, dd in json.load(fh).items():
                    out.setdefault(s, {}).update(dd)
    return out


def liquid_by_day(R):
    """{date: set(symbols)} passing the floor, from the trailing 60 sessions (not today's)."""
    ok = {}
    for s, dd in R.items():
        if s in ("SPY", "QQQ", "IWM"):
            continue
        ds = sorted(dd)
        vols = [dd[d]["v"] for d in ds]
        run = 0.0
        for i, d in enumerate(ds):
            if i >= 60:
                avg = run / 60.0
                prev_c = dd[ds[i - 1]]["c"]
                if avg >= bot_data.MIN_VOLUME and prev_c >= bot_data.MIN_PRICE:
                    ok.setdefault(d, set()).add(s)
                run -= vols[i - 60]
            run += vols[i]
    return ok


def run_bot(R, ok, sizing):
    per_run, per_day, day_risk = SIZINGS[sizing]
    trades = []
    for d in sorted(ok):
        taken, risk = set(), 0.0
        for hhmm in DECISIONS:
            room = max(0, min(per_run, per_day - len(taken), int((day_risk - risk) // 10.0)))
            if room == 0:
                break
            cands = []
            for s in ok[d]:
                r = R[s].get(d, {}).get("d", {}).get(hhmm)
                if r and s not in taken:
                    cands.append((-r[0], s, r))
            for _, s, r in sorted(cands)[:room]:
                trades.append({"day": d, "sym": s, "pnl": r[2], "how": r[4]})
                taken.add(s)
                risk += r[3]
    return trades


def run_scanner(R, ok):
    trades = []
    for d in sorted(ok):
        cands = sorted((r[1], s, r) for s in ok[d] for r in [R[s].get(d, {}).get("d", {}).get(SCAN_AT)] if r)
        for _, s, r in cands[:paper.SCANNER_CFG["picks"]]:
            trades.append({"day": d, "sym": s, "pnl": r[2], "how": r[4]})
    return trades


def tstat(xs):
    n = len(xs)
    if n < 3:
        return 0.0
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m / sd * math.sqrt(n) if sd else 0.0


def summary(trades):
    by = {}
    for t in trades:
        by[t["day"]] = by.get(t["day"], 0.0) + t["pnl"]
    years = {}
    for d, v in by.items():
        years.setdefault(d[:4], []).append(v)
    p = [t["pnl"] for t in trades]
    return {"trades": len(p), "net_usd": round(sum(p), 2), "per_trade": round(sum(p) / len(p), 3) if p else 0.0,
            "win_rate": round(sum(1 for x in p if x > 0) / len(p), 3) if p else None, "days": len(by),
            "t_daily": round(tstat(list(by.values())), 2),
            "years": {y: {"net_usd": round(sum(v), 2), "t": round(tstat(v), 2)} for y, v in sorted(years.items())}}


def cmd_stocks(a):
    R = load_records()
    ok = liquid_by_day(R)
    days = sorted(ok)
    print("Alpaca SIP 5-minute records: %d names, %d sessions %s to %s." % (len(R), len(days), days[0], days[-1]))
    out = {"names": len(R), "from": days[0], "to": days[-1], "sessions": len(days), "tracks": {}}
    for name, tr in (("bot_old_5_a_day", run_bot(R, ok, "old")), ("bot_now_50_a_day", run_bot(R, ok, "now")),
                     ("scanner_3_at_0950", run_scanner(R, ok))):
        s = summary(tr)
        pos = sum(1 for y in s["years"].values() if y["net_usd"] > 0)
        s["verdict"] = "PASS (backtest only)" if s["t_daily"] >= 3 and pos >= 6 else "FAIL"
        out["tracks"][name] = s
        print("  %-18s %6d trades  net $%+10.2f  ($%+.2f a trade)  win %.0f%%  daily t %+.2f  years positive %d/%d  %s" % (
            name, s["trades"], s["net_usd"], s["per_trade"], 100 * (s["win_rate"] or 0), s["t_daily"], pos,
            len(s["years"]), s["verdict"]))
        print("      " + "  ".join("%s $%+.0f (t %+.1f)" % (y, v["net_usd"], v["t"]) for y, v in s["years"].items()))
    spy = R.get("SPY", {})
    sd = sorted(spy)
    if sd:
        out["spy_hold_x"] = round(spy[sd[-1]]["c"] / spy[sd[0]]["c"], 3)
        print("  SPY %s to %s: x%.2f (buy and hold)" % (sd[0], sd[-1], out["spy_hold_x"]))
    print("History, not a forecast. Research, not financial advice.")
    if a.write:
        with open(RESULT, "w") as fh:
            json.dump(out, fh, indent=1)
        print("Wrote %s" % os.path.relpath(RESULT, HERE))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="multi-year Alpaca 5-minute history and the stock bots on it")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("fetch")
    p.add_argument("--from", dest="frm", default="2019-01")
    p.add_argument("--to", default="2026-11")
    p.add_argument("--top", type=int, default=500)
    p = sub.add_parser("stocks")
    p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    fn = {"fetch": cmd_fetch, "stocks": cmd_stocks}.get(a.cmd)
    if not fn:
        ap.print_help()
        return 1
    try:
        return fn(a)
    except alpaca_days.AlpacaError as e:
        print("alpaca_bars: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
