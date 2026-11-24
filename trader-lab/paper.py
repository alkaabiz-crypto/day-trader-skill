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
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402
import costs  # noqa: E402

ROOT = os.path.dirname(HERE)
SCAN = os.path.join(ROOT, "trader-scanner", "scan.py")
SCANNER_DIR = os.path.join(HERE, "paper", "scanner")
SCANNER_CFG = {"at": "09:50", "picks": 3, "risk_usd": 10.0, "budget_usd": 1000.0, "target_r": 1.0,
               "max_cost_share": 0.10, "slip_bps": 1.0}

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
    # Exness stress: the same trades if the round trip cost stress_cost_bps instead of cost_bps (a wider
    # spread at 15:30-15:55 than assumed). Added 2026-11-24; it only makes the bar stricter.
    def gross_of(r):
        return float(r["gross_bps"]) if r.get("gross_bps") not in (None, "") else float(r["net_bps"]) + cfg["cost_bps"]

    def notional_of(r):
        return float(r["notional_usd"]) if r.get("notional_usd") not in (None, "") else cfg["budget_usd"]
    stress = cfg.get("stress_cost_bps")
    stress_pnl = None
    if stress is not None:
        stress_pnl = sum((gross_of(r) - stress) / 1e4 * notional_of(r) for r in sh)
    gross = [gross_of(r) for r in sh]
    checks = {"net_positive": sum(pnl) > 0, "t_ok": t >= bar["min_t"], "drawdown_ok": mdd < bar["max_drawdown_usd"],
              "demo_lag_ok": lag is None or lag <= bar["max_demo_lag"]}
    if stress is not None:
        checks["stress_net_positive"] = stress_pnl > 0
    # Daily t (added 2026-11-24, stricter only): the 2-3 trades of one day are ~0.93 correlated
    # (power.py), so each day's P&L counts as one observation. Required alongside the per-trade t.
    by_day = {}
    for r, x in zip(sh, pnl):
        by_day[r["date"]] = by_day.get(r["date"], 0.0) + x
    dv = list(by_day.values())
    t_daily = (statistics.mean(dv) / statistics.stdev(dv) * math.sqrt(len(dv))) if len(dv) > 2 and statistics.stdev(dv) > 0 else 0.0
    checks["daily_t_ok"] = t_daily >= bar["min_t"]
    verdict = "IN PROGRESS" if not enough else ("PASS" if all(checks.values()) else "FAIL")
    return {"days": n_days, "trades": len(sh), "net_usd": round(sum(pnl), 2),
            "mean_net_bps": round(statistics.mean(nets), 2) if nets else 0.0, "t": round(t, 2),
            "max_drawdown_usd": round(mdd, 2), "win_rate": (sum(1 for x in nets if x > 0) / len(nets)) if nets else 0.0,
            "demo_trades": len(demo), "demo_lag": lag, "checks": checks, "verdict": verdict,
            "stress_cost_bps": stress, "stress_net_usd": None if stress_pnl is None else round(stress_pnl, 2),
            "break_even_cost_bps": round(statistics.mean(gross), 2) if gross else None,
            "t_daily": round(t_daily, 2), "trade_days": len(dv)}


# ---------------------------------------------------------------- scanner track (simulated, automatic)

def slot_of(hhmm):
    h, m = map(int, hhmm.split(":"))
    return (h * 60 + m - lab.OPEN_MIN) // 5


def scanner_plan(hit, bars_so_far, watch, cfg=SCANNER_CFG):
    """One orb hit -> a long plan, or None. Stop at the opening-range midpoint, target at target_r x risk,
    whole shares so the stop loses at most risk_usd and the position is at most budget_usd.
    Skipped when the estimated round trip (Corwin-Schultz on today's 5-minute bars + slippage) eats more
    than max_cost_share of the reward."""
    entry = float(hit["price"])
    stop = round((float(hit["or_high"]) + float(hit["or_low"])) / 2.0, 2)
    if stop >= entry:
        return None
    risk = entry - stop
    target = round(entry + cfg["target_r"] * risk, 2)
    shares = int(min(cfg["risk_usd"] / risk, cfg["budget_usd"] / entry))
    if shares < 1:
        return None
    sp = [x for x in costs.cs_spread([b["h"] for b in bars_so_far], [b["l"] for b in bars_so_far],
                                     [b["c"] for b in bars_so_far]) if x is not None]
    spread_bps = statistics.median(sp) * 1e4 if sp else 5.0
    cost_bps = spread_bps + 2 * cfg["slip_bps"] + costs.SEC_FEE_BPS
    reward_bps = (target - entry) / entry * 1e4
    if cost_bps > cfg["max_cost_share"] * reward_bps:
        return None
    return {"symbol": hit["symbol"], "side": "buy", "entry_est": entry, "stop": stop, "target": target,
            "shares": shares, "max_loss_usd": round(shares * risk, 2), "cost_bps": round(cost_bps, 2),
            "reward_bps": round(reward_bps, 1), "premarket_hit": hit["symbol"] in watch,
            "or_low": hit["or_low"], "or_high": hit["or_high"], "pct_over": hit.get("pct_over")}


def pick_scanner(hits, watch, n):
    """Pre-market watchlist names first, then the freshest breakouts (least extended over the range)."""
    return sorted(hits, key=lambda h: (h["symbol"] not in watch, h.get("pct_over", 99), h["symbol"]))[:n * 4]


def fill_long(bars, start_slot, stop, target, exit_slot=EXIT_SLOT):
    """Enter at the open of start_slot; a bar touching both stop and target counts as the stop.
    -> (entry, exit, how)."""
    e = bars[start_slot]["o"]
    for i in range(start_slot, exit_slot + 1):
        b = bars[i]
        if b["l"] <= stop:
            return e, (min(stop, b["o"]) if i > start_slot else min(stop, e)), "stop"
        if b["h"] >= target:
            return e, (max(target, b["o"]) if i > start_slot else max(target, e)), "target"
    return e, bars[exit_slot]["c"], "close"


def cmd_scanner(a):
    """Whole-market opening-range breakout scan at --at (default 09:50 New York), the best picks
    planned and saved for the automatic simulated fill. Nothing is placed anywhere."""
    cfg = dict(SCANNER_CFG)
    at = a.at or cfg["at"]
    cmd = [sys.executable, SCAN, "orb", "--at", at, "--json", "--no-write"]
    if a.now:
        cmd += ["--now", a.now]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    try:
        doc = json.loads(out.stdout)
    except ValueError:
        raise PaperError("the orb scan failed: %s" % (out.stderr.strip()[-300:] or out.stdout.strip()[-300:]))
    watch = set()
    wl = os.path.join(ROOT, "trader", "watchlist.json")
    if os.path.exists(wl):
        with open(wl) as fh:
            w = json.load(fh)
        if w.get("mode") == "daily":
            watch = {h["symbol"] for h in w.get("hits", [])}
    date = doc["as_of"][:10]
    plans = []
    for h in pick_scanner(doc.get("hits", []), watch, cfg["picks"]):
        if len(plans) >= cfg["picks"]:
            break
        try:
            sess = lab.sessions_of(lab.parse_chart(lab.fetch_chart(h["symbol"])))
        except lab.LabError:
            continue
        today = dict(sess).get(date) or []
        p = scanner_plan(h, today[:slot_of(at)], watch, cfg)
        if p:
            p["date"], p["decided_at"] = date, at
            plans.append(p)
    os.makedirs(SCANNER_DIR, exist_ok=True)
    with open(os.path.join(SCANNER_DIR, "%s.json" % date), "w") as fh:
        json.dump(plans, fh, indent=1)
    print("Scanner track (SIMULATED, automatic), %s %s New York: %d breakouts in %s charts; picked %d." % (
        date, at, len(doc.get("hits", [])), "{:,}".format(doc.get("scanned", 0)), len(plans)))
    for p in plans:
        print("  BUY %-6s ~%.2f  %d sh  stop %.2f  target %.2f  max loss $%.2f  cost %.1f bp of %.0f bp reward%s" % (
            p["symbol"], p["entry_est"], p["shares"], p["stop"], p["target"], p["max_loss_usd"], p["cost_bps"],
            p["reward_bps"], "  (also a pre-market hit)" if p["premarket_hit"] else ""))
    print("Filled automatically from real 5-minute prices after the close (paper.py log). No order is placed.")
    return 0


def log_scanner(date, plans):
    rows = []
    for p in plans:
        sess = dict(lab.sessions_of(lab.parse_chart(lab.fetch_chart(p["symbol"]))))
        bars = sess.get(date)
        if not bars or len(bars) <= EXIT_SLOT:
            continue
        e, x, how = fill_long(bars, slot_of(p["decided_at"]), p["stop"], p["target"])
        notional = p["shares"] * e
        cost_usd = notional * p["cost_bps"] / 1e4
        pnl = p["shares"] * (x - e) - cost_usd
        rows.append({"date": date, "source": "scanner-sim", "instrument": p["symbol"], "proxy": p["symbol"],
                     "side": "buy", "move_bps": p.get("pct_over", ""), "entry": round(e, 4), "exit": round(x, 4),
                     "stopped": int(how == "stop"), "gross_bps": round((x / e - 1) * 1e4, 2),
                     "cost_bps": p["cost_bps"], "net_bps": round(pnl / notional * 1e4, 2),
                     "notional_usd": round(notional, 2), "pnl_usd": round(pnl, 2)})
    return rows


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
    print("These are SIMULATED automatically (filled and logged after the close); placing them on the demo is optional.")
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
    logged_sc = {r["date"] for r in rows if r["source"] in ("scanner-sim", "scanner-day")}
    if os.path.isdir(SCANNER_DIR):
        for f in sorted(os.listdir(SCANNER_DIR)):
            d = f[:-5]
            if not f.endswith(".json") or d in logged_sc or d >= ny_now().date().isoformat() and ny_now().hour < 16:
                continue
            with open(os.path.join(SCANNER_DIR, f)) as fh:
                plans = json.load(fh)
            got = log_scanner(d, plans)
            new += got if got else [{"date": d, "source": "scanner-day"}]
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
    print("Daily t (each trading day's P&L one observation, %d days): %.2f %s." % (
        r["trade_days"], r["t_daily"], "ok" if r["checks"]["daily_t_ok"] else "no"))
    print("Bar (needs %d+ days and %d+ trades): net > 0 %s | t >= %.1f %s | drawdown < $%.0f %s | demo lag <= %.0f%% %s" % (
        bar["min_days"], bar["min_trades"], "ok" if r["checks"]["net_positive"] else "no", bar["min_t"],
        "ok" if r["checks"]["t_ok"] else "no", bar["max_drawdown_usd"], "ok" if r["checks"]["drawdown_ok"] else "no",
        bar["max_demo_lag"] * 100, "ok" if r["checks"]["demo_lag_ok"] else "no"))
    if r.get("stress_cost_bps") is not None:
        print("Cost stress: at %.1f bp a round trip (vs %.1f assumed) net $%+.2f %s; the trial breaks even at %s bp a trade. "
              "Swap: none (every trade is flat by 15:55 New York, before Exness's rollover)." % (
                  r["stress_cost_bps"], cfg["cost_bps"], r["stress_net_usd"],
                  "ok" if r["checks"].get("stress_net_positive") else "no",
                  "n/a" if r["break_even_cost_bps"] is None else "%.1f" % r["break_even_cost_bps"]))
    print("Verdict: %s. Paper trading only; going live is your decision. Not financial advice." % r["verdict"])
    sc = [x for x in rows if x["source"] == "scanner-sim"]
    if sc:
        pnl = [float(x["pnl_usd"]) for x in sc]
        print("Scanner track (simulated, not part of the bar): %d trades on %d days, net $%+.2f, win rate %.0f%%." % (
            len(sc), len({x["date"] for x in sc}), sum(pnl), 100.0 * sum(1 for v in pnl if v > 0) / len(pnl)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="trader-lab paper trial (Exness demo, placed by hand)")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("scanner", help="whole-market ORB scan at 09:50 New York -> simulated picks")
    p.add_argument("--at", help="New York time of the decision (default 09:50)")
    p.add_argument("--now", help='pretend it is this New York time, "YYYY-MM-DD HH:MM"')
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
        fn = {"tickets": cmd_tickets, "log": cmd_log, "record": cmd_record, "report": cmd_report,
              "scanner": cmd_scanner}.get(a.cmd)
        if not fn:
            ap.print_help()
            return 1
        return fn(a)
    except (PaperError, lab.LabError) as e:
        print("paper.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
