#!/usr/bin/env python3
"""Autopaper: the bots trade on their own, every market hour, on PAPER only.

    python3 autopaper.py run [--now "2026-11-24 10:52"]   # one hourly pass: manage positions, then buy on signals
    python3 autopaper.py report                           # equity, P&L, trades, vs SPY, verdict

The skills already in this repo decide, and nobody approves each trade:
  1. trader-scanner  scan.py orb       opening-range breakouts on the lab's 40 liquid names
  2. trader-entry    entry.py check    the breakout is still live (last close above the range high)
  3. trader-exit     exit.py plan      stop at the range midpoint, target 2R, flat by 15:55
  4. trader-budget   size.py           shares for the account and the $ risk limit
  5. trader-risk     check.py          PASS or BLOCK against the limits
  On a PASS the order is filled on paper at the last 5-minute close plus slippage. Nothing here talks to a
  broker: there is no order code at all. Going live is the owner's decision, and only after the verdict below.

FROZEN 2026-11-24 before the first run (config.json is written from CONFIG on the first run):
  $10,000 virtual account; $50 max loss a trade; max 3 open positions; max 4 buys a day; no new buys after
  15:00 New York or once the day is down $150; everything sold at the first run at or after 15:50; 2 bps
  slippage on entry and 5 bps round-trip costs. Stop and target are checked on every 5-minute bar since entry;
  a bar that touches both counts as the stop.
  Verdict: PAPER until 60 trading days. Then LIVE-REVIEW only if net P&L > 0, it beats SPY bought and held over
  the same days on the same $10,000, and the daily P&L t >= 2; otherwise FAIL. It's evidence for the
  owner to weigh, not a switch.
Research, not financial advice.
"""

import argparse
import csv
import datetime
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

BOOK = os.path.join(HERE, "autopaper")
RESULT = os.path.join(HERE, "results", "autopaper.json")
CONFIG = {"start_cash": 10000.0, "risk_usd": 50.0, "max_open": 3, "max_buys_day": 4, "daily_stop_usd": 150.0,
          "last_entry": "15:00", "flatten_at": "15:50", "slip_bps": 2.0, "cost_bps_round_trip": 5.0,
          "fresh_minutes": 60, "min_days": 60, "min_t": 2.0, "frozen": "2026-11-24"}
TRADE_FIELDS = ["date", "symbol", "qty", "entry_time", "entry", "stop", "target", "exit_time", "exit", "why",
                "gross_usd", "cost_usd", "pnl_usd"]
NY = "America/New_York"


# ---------------------------------------------------------------- clock and data

def ny_now(text=None):
    if text:
        return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")
    utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, second=0, microsecond=0)
    return utc_to_ny(utc)


def utc_to_ny(utc):
    """US Eastern time: daylight time from the 2nd Sunday of March 2:00 to the 1st Sunday of November 2:00."""
    y = utc.year
    mar = datetime.datetime(y, 3, 8) + datetime.timedelta(days=(6 - datetime.date(y, 3, 8).weekday()) % 7)
    nov = datetime.datetime(y, 11, 1) + datetime.timedelta(days=(6 - datetime.date(y, 11, 1).weekday()) % 7)
    dst = mar + datetime.timedelta(hours=7) <= utc < nov + datetime.timedelta(hours=6)  # 2:00 local in UTC
    return utc - datetime.timedelta(hours=4 if dst else 5)


def yahoo_bars(sym, day, now):
    """Completed 5-minute bars of `day` (New York) up to `now`: [{"t": "HH:MM", "o","h","l","c"}]."""
    import daily
    url = "https://query2.finance.yahoo.com/v8/finance/chart/%s?interval=5m&range=5d" % sym
    req = urllib.request.Request(url, headers={"User-Agent": daily.UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode("utf-8", "replace"))["chart"]["result"][0]
    off = (res.get("meta") or {}).get("gmtoffset", -18000) or -18000
    q = res["indicators"]["quote"][0]
    out = []
    for i, ts in enumerate(res.get("timestamp") or []):
        t = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts) + off)
        if t.date() != day or t + datetime.timedelta(minutes=5) > now:
            continue
        o, h, l, c = (q[k][i] for k in ("open", "high", "low", "close"))
        if None in (o, h, l, c) or t.minute % 5:
            continue
        out.append({"t": t.strftime("%H:%M"), "o": o, "h": h, "l": l, "c": c})
    return out


def run_skill(args, timeout=180):
    try:
        p = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timed out"
    try:
        return json.loads(p.stdout), None
    except ValueError:
        err = (p.stderr or p.stdout or "").strip().splitlines()
        return None, (err[-1] if err else "exit %d" % p.returncode)[:200]


# ---------------------------------------------------------------- book

def load_state():
    p = os.path.join(BOOK, "state.json")
    if os.path.exists(p):
        with open(p) as fh:
            return json.load(fh)
    return {"cash": CONFIG["start_cash"], "positions": [], "buys": {}, "realized": {}, "start": None}


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=1)
    os.replace(tmp, path)


def append_csv(name, fields, rows):
    p = os.path.join(BOOK, name)
    new = not os.path.exists(p)
    os.makedirs(BOOK, exist_ok=True)
    with open(p, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def close_trade(state, pos, exit_px, when, why, cfg=CONFIG):
    qty = pos["qty"]
    gross = (exit_px - pos["entry"]) * qty
    cost = (pos["entry"] + exit_px) * qty * cfg["cost_bps_round_trip"] / 2 / 1e4
    pnl = gross - cost
    state["cash"] += exit_px * qty - cost
    d = when[:10]
    state["realized"][d] = state["realized"].get(d, 0.0) + pnl
    return {"date": pos["date"], "symbol": pos["symbol"], "qty": qty, "entry_time": pos["entry_time"],
            "entry": round(pos["entry"], 4), "stop": pos["stop"], "target": pos["target"], "exit_time": when,
            "exit": round(exit_px, 4), "why": why, "gross_usd": round(gross, 2), "cost_usd": round(cost, 2),
            "pnl_usd": round(pnl, 2)}


def manage(state, bars_of, now, cfg=CONFIG):
    """Check every open position against its bars since entry; sell at stop, target or the end of day."""
    closed, keep, marks = [], [], {}
    flatten = now.strftime("%H:%M") >= cfg["flatten_at"]
    for pos in state["positions"]:
        bars = bars_of(pos["symbol"])
        done = None
        stale = pos["date"] < now.date().isoformat()
        for b in bars:
            if not stale and b["t"] < pos["entry_bar_end"]:
                continue
            if b["l"] <= pos["stop"]:
                px = min(b["o"], pos["stop"])          # a gap below the stop fills at the open
                done = (px, "%s %s" % (now.date(), b["t"]), "stop")
                break
            if b["h"] >= pos["target"]:
                px = max(b["o"], pos["target"]) if b["o"] > pos["target"] else pos["target"]
                done = (px, "%s %s" % (now.date(), b["t"]), "target")
                break
        if done is None and (flatten or stale) and bars:
            done = (bars[-1]["c"], "%s %s" % (now.date(), bars[-1]["t"]), "end of day" if not stale else "stale")
        if done:
            closed.append(close_trade(state, pos, done[0], done[1], done[2], cfg))
        else:
            if bars:
                marks[pos["symbol"]] = bars[-1]["c"]
            keep.append(pos)
    state["positions"] = keep
    return closed, marks


def equity(state, marks):
    return state["cash"] + sum(p["qty"] * marks.get(p["symbol"], p["entry"]) for p in state["positions"])


def day_pnl(state, marks, day):
    unreal = sum(p["qty"] * (marks.get(p["symbol"], p["entry"]) - p["entry"]) for p in state["positions"])
    return state["realized"].get(day, 0.0) + unreal


def may_buy(state, marks, now, cfg=CONFIG):
    day = now.date().isoformat()
    if now.strftime("%H:%M") >= cfg["last_entry"]:
        return False, "after %s, no new buys" % cfg["last_entry"]
    if day_pnl(state, marks, day) <= -cfg["daily_stop_usd"]:
        return False, "daily loss stop hit"
    if len(state["positions"]) >= cfg["max_open"]:
        return False, "max open positions"
    if state["buys"].get(day, 0) >= cfg["max_buys_day"]:
        return False, "max buys today"
    return True, ""


# ---------------------------------------------------------------- the bots' decision chain

def find_buys(state, marks, now, symbols, live_now, cfg=CONFIG, skill=run_skill):
    """scan -> entry -> exit -> size -> risk. Returns new positions (paper fills) and a log of decisions."""
    log, new = [], []
    ok, why = may_buy(state, marks, now, cfg)
    if not ok:
        return new, [why]
    nowarg = [] if live_now else ["--now", now.strftime("%Y-%m-%d %H:%M")]
    scan, err = skill(["trader-scanner/scan.py", "orb", "--symbols", ",".join(symbols), "--no-write", "--json"]
                      + nowarg)
    if scan is None:
        return new, ["scanner failed: %s" % err]
    held = {p["symbol"] for p in state["positions"]}
    traded_today = set(state.get("traded", {}).get(now.date().isoformat(), []))
    hits = [h for h in scan.get("hits", []) if h["symbol"] not in held and h["symbol"] not in traded_today]
    log.append("scanner: %d breakouts" % len(hits))
    tmp = tempfile.mkdtemp(prefix="autopaper-")
    for h in hits:
        ok, why = may_buy(state, marks, now, cfg)
        if not ok:
            log.append(why)
            break
        s = h["symbol"]
        ep = os.path.join(tmp, s + "-entry.json")
        ent, err = skill(["trader-entry/entry.py", "check", s, "--setup", "orb", "--write", ep, "--json"] + nowarg)
        if not ent or ent.get("status") != "triggered":
            log.append("%s: entry %s" % (s, (ent or {}).get("status", err)))
            continue
        last = ent.get("last") or {}
        if (ent.get("minutes_since") or 0) > cfg["fresh_minutes"] + 60 or (last.get("vs_level_pct") or -1) < 0:
            log.append("%s: breakout no longer live (last close %s%% vs the range high)" % (s, last.get("vs_level_pct")))
            continue
        px = round(last["close"] * (1 + cfg["slip_bps"] / 1e4), 4)
        pp = os.path.join(tmp, s + "-plan.json")
        plan, err = skill(["trader-exit/exit.py", "plan", "--from", ep, "--entry", str(px), "--write", pp, "--json"])
        if not plan or plan.get("stop") is None or plan["stop"] >= px:
            log.append("%s: no valid exit plan (%s)" % (s, err))
            continue
        avail = state["cash"]
        cp = os.path.join(tmp, s + "-cfg.json")
        with open(cp, "w") as fh:
            json.dump({"budget": round(avail, 2), "max_loss_per_trade_usd": cfg["risk_usd"],
                       "max_daily_loss_usd": cfg["daily_stop_usd"], "max_trades_per_day": cfg["max_buys_day"],
                       "paper": True}, fh)
        op = os.path.join(tmp, s + "-orders.json")
        size, err = skill(["trader-budget/size.py", "--plan", pp, "--config", cp, "--budget", str(round(avail, 2)),
                           "--write", op, "--json"])
        qty = int(((size or {}).get("sizing") or size or {}).get("qty") or 0)
        if qty <= 0:
            log.append("%s: size 0 (%s)" % (s, err))
            continue
        risk, err = skill(["trader-risk/check.py", "--orders", op, "--config", cp, "--no-write", "--json"] + nowarg)
        verdict = ((risk or {}).get("results") or [{}])[0].get("verdict")
        if verdict != "PASS":
            log.append("%s: risk %s %s" % (s, verdict or err, ((risk or {}).get("results") or [{}])[0].get("reasons")))
            continue
        pos = {"symbol": s, "qty": qty, "entry": px, "stop": plan["stop"], "target": plan["target"],
               "date": now.date().isoformat(), "entry_time": now.strftime("%Y-%m-%d %H:%M"),
               "entry_bar_end": now.replace(minute=now.minute - now.minute % 5).strftime("%H:%M")}
        # ^ the bar the fill happened in is checked too, so a stop hit in it isn't missed
        state["cash"] -= px * qty
        state["positions"].append(pos)
        d = now.date().isoformat()
        state["buys"][d] = state["buys"].get(d, 0) + 1
        state.setdefault("traded", {}).setdefault(d, []).append(s)
        new.append(pos)
        log.append("%s: BUY %d @ %.2f, stop %.2f, target %.2f (paper)" % (s, qty, px, plan["stop"], plan["target"]))
    return new, log


# ---------------------------------------------------------------- commands

def cmd_run(a):
    import lab
    now = ny_now(a.now)
    day = now.date()
    state = load_state()
    if not os.path.exists(os.path.join(BOOK, "config.json")):
        save_json(os.path.join(BOOK, "config.json"), CONFIG)
    cache = {}

    def bars_of(sym):
        if sym not in cache:
            try:
                cache[sym] = yahoo_bars(sym, day, now)
            except Exception:  # noqa: BLE001
                cache[sym] = []
        return cache[sym]

    if not bars_of("SPY"):
        line = "%s market closed or no data: nothing done" % now.strftime("%Y-%m-%d %H:%M")
        print(line)
        append_csv("runs.csv", ["time", "summary"], [{"time": now.strftime("%Y-%m-%d %H:%M"), "summary": line}])
        return 0
    state["start"] = state["start"] or day.isoformat()
    closed, marks = manage(state, bars_of, now)
    new, log = find_buys(state, marks, now, lab.UNIVERSE, live_now=a.now is None)
    for p in new:
        marks[p["symbol"]] = p["entry"]
    eq = equity(state, marks)
    append_csv("trades.csv", TRADE_FIELDS, closed)
    append_csv("equity.csv", ["time", "cash", "open", "equity"],
               [{"time": now.strftime("%Y-%m-%d %H:%M"), "cash": round(state["cash"], 2),
                 "open": len(state["positions"]), "equity": round(eq, 2)}])
    save_json(os.path.join(BOOK, "state.json"), state)
    sold = ["%s %s %+.2f" % (t["symbol"], t["why"], t["pnl_usd"]) for t in closed]
    line = "%s equity $%.2f | sold: %s | %s" % (now.strftime("%Y-%m-%d %H:%M"), eq, ", ".join(sold) or "none",
                                                "; ".join(log))
    append_csv("runs.csv", ["time", "summary"], [{"time": now.strftime("%Y-%m-%d %H:%M"), "summary": line}])
    print(line)
    write_report()
    return 0


def tstat(x):
    if len(x) < 3 or statistics.stdev(x) == 0:
        return 0.0
    return statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x)))


def write_report(spy_fn=None):
    state = load_state()
    trades, eq_rows = [], []
    for name, sink in (("trades.csv", trades), ("equity.csv", eq_rows)):
        p = os.path.join(BOOK, name)
        if os.path.exists(p):
            with open(p) as fh:
                sink.extend(csv.DictReader(fh))
    last_by_day = {}
    for r in eq_rows:
        last_by_day[r["time"][:10]] = float(r["equity"])
    days = sorted(last_by_day)
    eqs = [CONFIG["start_cash"]] + [last_by_day[d] for d in days]
    daily_pnl = [b - a for a, b in zip(eqs, eqs[1:])]
    peak, mdd = eqs[0], 0.0
    for e in eqs:
        peak = max(peak, e)
        mdd = max(mdd, peak - e)
    pnls = [float(t["pnl_usd"]) for t in trades]
    out = {"frozen": CONFIG["frozen"], "start": state.get("start"), "days": len(days),
           "equity": eqs[-1], "pnl_usd": eqs[-1] - CONFIG["start_cash"], "trades": len(pnls),
           "win_rate": (sum(p > 0 for p in pnls) / len(pnls)) if pnls else None,
           "max_drawdown_usd": mdd, "open_positions": len(state["positions"]), "daily_t": tstat(daily_pnl)}
    spy = None
    if days:
        try:
            spy = (spy_fn or spy_return)(days[0], days[-1])
        except Exception:  # noqa: BLE001
            spy = None
    out["spy_same_days_usd"] = None if spy is None else CONFIG["start_cash"] * spy
    if out["days"] < CONFIG["min_days"]:
        out["verdict"] = "PAPER"
    else:
        beat = spy is not None and out["pnl_usd"] > out["spy_same_days_usd"]
        out["verdict"] = "LIVE-REVIEW" if (out["pnl_usd"] > 0 and beat and out["daily_t"] >= CONFIG["min_t"]) else "FAIL"
    save_json(RESULT, out)
    return out


def spy_return(first, last):
    """SPY from the close before `first` to the close of `last` (dividend-adjusted)."""
    import daily
    b = daily.parse_daily(daily.fetch_daily("SPY"))
    px = dict(zip(b["d"], b["a"]))
    before = [d for d in b["d"] if d < first]
    if not before or last not in px:
        return None
    return px[last] / px[before[-1]] - 1.0


def cmd_report(a):
    r = write_report()
    print("Autopaper since %s: %d days, %d trades, equity $%.2f (P&L %+.2f, SPY same days %s), max drawdown $%.2f, "
          "open %d -> %s" % (r["start"], r["days"], r["trades"], r["equity"], r["pnl_usd"],
                             "n/a" if r["spy_same_days_usd"] is None else "%+.2f" % r["spy_same_days_usd"],
                             r["max_drawdown_usd"], r["open_positions"], r["verdict"]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--now", help='New York time "YYYY-MM-DD HH:MM" (default: now)')
    sub.add_parser("report")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "report":
        return cmd_report(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
