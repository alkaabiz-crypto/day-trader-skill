#!/usr/bin/env python3
"""trader-lab paper: a pre-registered paper day-trading trial, placed by hand on an Exness demo.

    python3 paper.py tickets                 # at 15:31 New York: today's tickets, if the rule fires
    python3 paper.py log                     # after the close: shadow-fill every ticket into the journal
    python3 paper.py record --date 2026-11-24 --instrument US500 --side sell --pnl -3.20
    python3 paper.py report                  # progress against the pre-registered bar

The rule, limits and pass bar are in paper/PLAN.md and paper/config.json, written before the
first trade. Signals come from ETF proxies (SPY for US500, QQQ for USTEC, DIA for US30) using
Yahoo's 5-minute bars. The shadow log simulates every ticket from those bars, so the record is
complete even on days nobody trades. Nothing here places an order. Research, not financial advice.
"""

import argparse
import csv
import datetime
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402

PAPER = os.path.join(HERE, "paper")
CONFIG = os.path.join(PAPER, "config.json")
JOURNAL = os.path.join(PAPER, "journal.csv")
TICKETS = os.path.join(PAPER, "tickets")
FIELDS = ["date", "source", "instrument", "proxy", "side", "move_bps", "entry", "exit", "stopped",
          "gross_bps", "cost_bps", "net_bps", "notional_usd", "pnl_usd"]
SIGNAL_SLOT = 71          # the 15:25-15:30 bar: its close is the 15:30 price
ENTRY_SLOT = 72           # enter at the 15:30 bar's open
EXIT_SLOT = 76            # out at the close of the 15:50-15:55 bar (15:55)


class PaperError(Exception):
    pass


def load_config(path=CONFIG):
    if not os.path.exists(path):
        raise PaperError("no %s: the trial is not set up" % path)
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------- the rule

def signal(prev_close, price_1530, cfg):
    """Fade the move from yesterday's close to 15:30 when it is at least min_move_pct.
    -> (side, move_bps): side +1 buy, -1 sell, 0 no trade."""
    move = (price_1530 / prev_close - 1) * 1e4
    if abs(move) < cfg["min_move_pct"] * 100:
        return 0, move
    return (-1 if move > 0 else 1), move


def size(cfg):
    """Notional so the stop loses at most risk_per_trade_usd, never above the budget (no leverage)."""
    return min(cfg["budget_usd"], cfg["risk_per_trade_usd"] / (cfg["stop_pct"] / 100.0))


def tickets_for(day_bars, prev_bars, cfg):
    """day_bars: {proxy: [5-min bar dicts of today]}; prev_bars: {proxy: yesterday's full session}.
    -> list of tickets, largest moves first, within the daily trade and loss limits."""
    out = []
    for inst, proxy in sorted(cfg["instruments"].items()):
        b, pb = day_bars.get(proxy), prev_bars.get(proxy)
        if not b or not pb or len(b) <= SIGNAL_SLOT or len(pb) != lab.SESSION_BARS:
            continue
        side, move = signal(pb[-1]["c"], b[SIGNAL_SLOT]["c"], cfg)
        if side:
            out.append({"instrument": inst, "proxy": proxy, "side": "buy" if side > 0 else "sell",
                        "move_bps": round(move, 1), "proxy_1530": b[SIGNAL_SLOT]["c"],
                        "proxy_prev_close": pb[-1]["c"]})
    out.sort(key=lambda t: -abs(t["move_bps"]))
    n = int(min(cfg["max_trades_per_day"], cfg["max_daily_loss_usd"] // cfg["risk_per_trade_usd"]))
    notional = size(cfg)
    for t in out[:n]:
        t["notional_usd"] = round(notional, 2)
        t["max_loss_usd"] = round(notional * cfg["stop_pct"] / 100.0, 2)
        t["stop_pct"] = cfg["stop_pct"]
    return out[:n]


def shadow_fill(bars, side, cfg):
    """Enter at the 15:30 bar's open, stop at stop_pct, out at the 15:55 close.
    -> (entry, exit, stopped, gross_bps)."""
    if len(bars) <= EXIT_SLOT:
        raise PaperError("session too short for a fill")
    e = bars[ENTRY_SLOT]["o"]
    s = 1 if side == "buy" else -1
    stop = e * (1 - s * cfg["stop_pct"] / 100.0)
    for i in range(ENTRY_SLOT, EXIT_SLOT + 1):
        b = bars[i]
        if s > 0 and b["l"] <= stop:
            x = min(stop, b["o"]) if i > ENTRY_SLOT else stop
            return e, x, True, (x / e - 1) * 1e4
        if s < 0 and b["h"] >= stop:
            x = max(stop, b["o"]) if i > ENTRY_SLOT else stop
            return e, x, True, -(x / e - 1) * 1e4
    x = bars[EXIT_SLOT]["c"]
    return e, x, False, s * (x / e - 1) * 1e4


# ---------------------------------------------------------------- data

def proxy_sessions(proxies, now_utc=None):
    """{proxy: [(date, bars)]} from Yahoo's last 60 days of 5-minute bars (not saved)."""
    out = {}
    for p in proxies:
        out[p] = lab.sessions_of(lab.parse_chart(lab.fetch_chart(p), now_utc))
    return out


def day_and_prev(sess, date):
    dates = [d for d, _ in sess]
    if date not in dates:
        return None, None
    k = dates.index(date)
    prev = next((b for d, b in reversed(sess[:k]) if len(b) == lab.SESSION_BARS), None)
    return sess[k][1], prev


# ---------------------------------------------------------------- journal

def read_journal(path=JOURNAL):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def append_rows(rows, path=JOURNAL):
    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def log_day(sessions, date, cfg):
    """Shadow rows for one date: recompute the day's tickets from the bars (so a missed 15:31 run
    leaves no gap) and fill them."""
    day, prev = {}, {}
    for p, sess in sessions.items():
        b, pb = day_and_prev(sess, date)
        if b and len(b) == lab.SESSION_BARS:
            day[p], prev[p] = b, pb
    rows = []
    for t in tickets_for(day, prev, cfg):
        e, x, stopped, gross = shadow_fill(day[t["proxy"]], t["side"], cfg)
        net = gross - cfg["cost_bps"]
        rows.append({"date": date, "source": "shadow", "instrument": t["instrument"], "proxy": t["proxy"],
                     "side": t["side"], "move_bps": t["move_bps"], "entry": round(e, 4), "exit": round(x, 4),
                     "stopped": int(stopped), "gross_bps": round(gross, 2), "cost_bps": cfg["cost_bps"],
                     "net_bps": round(net, 2), "notional_usd": t["notional_usd"],
                     "pnl_usd": round(t["notional_usd"] * net / 1e4, 2)})
    return rows


# ---------------------------------------------------------------- report

def evaluate(rows, cfg):
    """Shadow results since the start date against the pre-registered bar."""
    bar = cfg["pass_bar"]
    sh = [r for r in rows if r["source"] == "shadow" and r["date"] >= cfg["start_date"]]
    nets = [float(r["net_bps"]) for r in sh]
    pnl = [float(r["pnl_usd"]) for r in sh]
    eq = peak = mdd = 0.0
    for x in pnl:
        eq += x
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    t = (statistics.mean(nets) / statistics.stdev(nets) * math.sqrt(len(nets))) if len(nets) > 2 and statistics.stdev(nets) > 0 else 0.0
    demo = [r for r in rows if r["source"] == "demo" and r["date"] >= cfg["start_date"]]
    lag = None
    if demo:
        keys = {(r["date"], r["instrument"]) for r in demo}
        sh_same = sum(float(r["pnl_usd"]) for r in sh if (r["date"], r["instrument"]) in keys)
        de = sum(float(r["pnl_usd"]) for r in demo)
        lag = (sh_same - de) / abs(sh_same) if sh_same else None
    n_days = len(set(cfg.get("_logged_days", [])) | {r["date"] for r in sh})
    enough = n_days >= bar["min_days"] and len(sh) >= bar["min_trades"]
    checks = {"net_positive": sum(pnl) > 0, "t_ok": t >= bar["min_t"], "drawdown_ok": mdd < bar["max_drawdown_usd"],
              "demo_lag_ok": lag is None or lag <= bar["max_demo_lag"]}
    verdict = "IN PROGRESS" if not enough else ("PASS" if all(checks.values()) else "FAIL")
    return {"days": n_days, "trades": len(sh), "net_usd": round(sum(pnl), 2),
            "mean_net_bps": round(statistics.mean(nets), 2) if nets else 0.0, "t": round(t, 2),
            "max_drawdown_usd": round(mdd, 2), "win_rate": (sum(1 for x in nets if x > 0) / len(nets)) if nets else 0.0,
            "demo_trades": len(demo), "demo_lag": lag, "checks": checks, "verdict": verdict}


# ---------------------------------------------------------------- commands

def ny_now():
    return lab.to_eastern(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


def server_time(ny_dt):
    """Exness server time is GMT: New York + 5 h (EST) or + 4 h (EDT)."""
    utc = lab.eastern_to_epoch(ny_dt)
    return datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=utc)


def cmd_tickets(a):
    cfg = load_config()
    now_utc = None
    if a.now:
        ny = datetime.datetime.strptime(a.now, "%Y-%m-%d %H:%M")
        now_utc = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=lab.eastern_to_epoch(ny))
    ny = lab.to_eastern(now_utc) if now_utc else ny_now()
    date = ny.date().isoformat()
    sess = proxy_sessions(sorted(set(cfg["instruments"].values())), now_utc)
    day, prev = {}, {}
    for p, s in sess.items():
        b, pb = day_and_prev(s, date)
        if b:
            day[p], prev[p] = b, pb
    if not day or all(len(b) <= SIGNAL_SLOT for b in day.values()):
        print("No 15:30 price yet for %s (New York time now %s). Run again after 15:30." % (date, ny.strftime("%H:%M")))
        return 0
    ts = tickets_for(day, prev, cfg)
    os.makedirs(TICKETS, exist_ok=True)
    with open(os.path.join(TICKETS, "%s.json" % date), "w") as fh:
        json.dump(ts, fh, indent=1)
    exit_ny = datetime.datetime.strptime(date + " " + cfg["flat_by"], "%Y-%m-%d %H:%M")
    print("PAPER trial, %s. Rule: fade a move of %.1f%%+ from yesterday's close to 15:30 New York." % (
        date, cfg["min_move_pct"]))
    if not ts:
        print("No ticket today: no index moved %.1f%% or more by 15:30." % cfg["min_move_pct"])
    for t in ts:
        print("  %-6s %-4s  notional $%.0f  stop %.2f%% from your fill (max loss $%.2f)  (%s moved %+.2f%%)" % (
            t["instrument"], t["side"].upper(), t["notional_usd"], t["stop_pct"], t["max_loss_usd"],
            t["proxy"], t["move_bps"] / 100.0))
    if ts:
        print("Place on the Exness DEMO account by %s New York (%s Exness server time); close by %s New York (%s server)." % (
            cfg["no_entries_after"], server_time(datetime.datetime.strptime(date + " " + cfg["no_entries_after"],
                                                                             "%Y-%m-%d %H:%M")).strftime("%H:%M"),
            cfg["flat_by"], server_time(exit_ny).strftime("%H:%M")))
        print("Volume in MT5 = notional / (index price x contract size). After closing, record the result:")
        print("  python3 trader-lab/paper.py record --date %s --instrument <US500|USTEC|US30> --side <buy|sell> --pnl <$>" % date)
    print("Paper trading only. Not financial advice.")
    return 0


def cmd_log(a):
    cfg = load_config()
    sess = proxy_sessions(sorted(set(cfg["instruments"].values())))
    rows = read_journal()
    done = {r["date"] for r in rows if r["source"] in ("shadow", "shadow-day")}
    dates = sorted({d for s in sess.values() for d, b in s if len(b) == lab.SESSION_BARS and d >= cfg["start_date"]})
    new = []
    for d in dates:
        if d in done:
            continue
        got = log_day(sess, d, cfg)
        new += got if got else [{"date": d, "source": "shadow-day"}]   # a day with no ticket still counts
    append_rows(new)
    print("Logged %d new row(s) for %d day(s)." % (len(new), len({r["date"] for r in new})))
    return 0


def cmd_record(a):
    cfg = load_config()
    append_rows([{"date": a.date, "source": "demo", "instrument": a.instrument.upper(), "side": a.side,
                  "pnl_usd": a.pnl, "notional_usd": a.notional or "", "entry": a.entry or "", "exit": a.exit or ""}])
    print("Recorded your demo trade: %s %s %s $%+.2f" % (a.date, a.instrument.upper(), a.side, a.pnl))
    return 0


def cmd_report(a):
    cfg = load_config()
    rows = read_journal()
    cfg["_logged_days"] = sorted({r["date"] for r in rows if r["source"] in ("shadow", "shadow-day")
                                  and r["date"] >= cfg["start_date"]})
    r = evaluate(rows, cfg)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    bar = cfg["pass_bar"]
    print("Paper trial since %s: %d trading days, %d shadow trades, net $%+.2f (%.2f bp a trade, t %.2f), "
          "max drawdown $%.2f, win rate %.0f%%." % (cfg["start_date"], r["days"], r["trades"], r["net_usd"],
                                                    r["mean_net_bps"], r["t"], r["max_drawdown_usd"], r["win_rate"] * 100))
    print("Your demo trades recorded: %d%s." % (r["demo_trades"], "" if r["demo_lag"] is None else
                                                ", lagging the shadow log by %.0f%%" % (r["demo_lag"] * 100)))
    print("Bar (needs %d+ days and %d+ trades): net > 0 %s | t >= %.1f %s | drawdown < $%.0f %s | demo lag <= %.0f%% %s" % (
        bar["min_days"], bar["min_trades"], "ok" if r["checks"]["net_positive"] else "no", bar["min_t"],
        "ok" if r["checks"]["t_ok"] else "no", bar["max_drawdown_usd"], "ok" if r["checks"]["drawdown_ok"] else "no",
        bar["max_demo_lag"] * 100, "ok" if r["checks"]["demo_lag_ok"] else "no"))
    print("Verdict: %s. Paper trading only; going live is your decision. Not financial advice." % r["verdict"])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="trader-lab paper trial (Exness demo, placed by hand)")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("tickets")
    p.add_argument("--now", help='pretend it is this New York time, "YYYY-MM-DD HH:MM"')
    sub.add_parser("log")
    p = sub.add_parser("record")
    p.add_argument("--date", required=True)
    p.add_argument("--instrument", required=True)
    p.add_argument("--side", required=True, choices=["buy", "sell"])
    p.add_argument("--pnl", type=float, required=True, help="the trade's profit or loss in $ from MT5")
    p.add_argument("--notional", type=float)
    p.add_argument("--entry", type=float)
    p.add_argument("--exit", type=float)
    p = sub.add_parser("report")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        fn = {"tickets": cmd_tickets, "log": cmd_log, "record": cmd_record, "report": cmd_report}.get(a.cmd)
        if not fn:
            ap.print_help()
            return 1
        return fn(a)
    except (PaperError, lab.LabError) as e:
        print("paper.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
