#!/usr/bin/env python3
"""Paper simulator: an automatic, fully simulated day-trading account.

It runs the pack's own rules end to end, on its own, with fake money:

  scanner   opening-range breakouts on today's most traded stocks (trader-scanner's scan_orb)
  entry     only a FRESH trigger: the breakout bar closed in the last `fresh_bars` bars
  exit      stop at the opening-range midpoint, target 1R (trader-exit's compute, to the cent)
  budget    shares = max loss per trade / risk a share, capped by the cash
  risk      max trades a day, daily loss limit, entry window, flat by 3:55 PM

Nothing here talks to a broker. There is no order, no API key and no real
account: the "fills" are bars from Yahoo's free chart API, written to
trader/paper/account.json. It exists so you can see how the rules would have
done before any real money, or even a real paper account, is involved.

    python3 paper/paper.py prepare        # today's most traded stocks -> trader/paper/liquid.json
    python3 paper/paper.py tick           # one pass: manage the open position, then look for an entry
    python3 paper/paper.py run            # tick after every 5-minute bar until the close
    python3 paper/paper.py status         # cash, open position, today's trades, profit and loss
    python3 paper/paper.py reset          # start over with the starting cash

Flags: --dir trader/paper, --now "2026-10-19 10:15" (New York time) to replay,
--offline FILE (a saved Yahoo v8 chart or a folder of them, as in trader-scanner).

Fills are simulated and honest about it: an entry fills at the close of the
last completed bar, a stop fills at the stop or at the bar's open if it gapped
through, a target at the target or a better open, and when one bar touches
both the stop and the target the stop is assumed to come first. Real fills
have spreads and slippage; these do not. Not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import sys
import time
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(folder, name):
    path = os.path.join(ROOT, folder, name + ".py")
    spec = importlib.util.spec_from_file_location("paper_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(mod)
    return mod


scan = _load("trader-scanner", "scan")
exitp = _load("trader-exit", "exit")

DEFAULTS = {
    "starting_cash": 5000.0,
    "max_loss_per_trade_usd": 50.0,
    "max_daily_loss_usd": 150.0,
    "max_trades_per_day": 3,
    "max_open": 1,
    "no_entries_before": "09:50",
    "no_entries_after": "15:30",
    "flat_by": "15:55",
    "or_minutes": 15,
    "target_r": 1.0,
    "liquid_count": 100,
    "min_price": 5.0,
    "max_confirm": 40,
    "fresh_bars": 2,
}
BAR = datetime.timedelta(minutes=5)
LAG = 25  # seconds after a bar closes before Yahoo reliably has it


class PaperError(Exception):
    pass


# ---------------------------------------------------------------- storage

class Book:
    def __init__(self, folder):
        self.dir = folder
        self.cfg_path = os.path.join(folder, "config.json")
        self.acct_path = os.path.join(folder, "account.json")
        self.log_path = os.path.join(folder, "log.jsonl")
        self.liquid_path = os.path.join(folder, "liquid.json")
        os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.cfg_path):
            self._write(self.cfg_path, DEFAULTS)
        with open(self.cfg_path, encoding="utf-8") as fh:
            user = json.load(fh)
        self.cfg = dict(DEFAULTS, **user)
        if os.path.exists(self.acct_path):
            with open(self.acct_path, encoding="utf-8") as fh:
                self.acct = json.load(fh)
        else:
            self.acct = self.fresh()
            self.save()

    def fresh(self):
        c = float(self.cfg["starting_cash"])
        return {"simulated": True, "starting_cash": c, "cash": c, "positions": [], "closed": []}

    def _write(self, path, doc):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
        os.replace(tmp, path)

    def save(self):
        self._write(self.acct_path, self.acct)

    def log(self, event):
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")

    def today(self, day):
        d = day.isoformat()
        entered = [p for p in self.acct["positions"] + self.acct["closed"] if p["day"] == d]
        pnl = sum(p["pnl"] for p in self.acct["closed"] if p["day"] == d)
        return entered, round(pnl, 2)


# ---------------------------------------------------------------- data

class Market:
    """Yahoo live, or saved charts with --offline (then every symbol in the file is the list)."""

    def __init__(self, offline=None):
        self.offline = None
        if offline:
            self.offline, _ = scan.load_offline(offline)
        self.cache = {}

    def chart(self, sym, rng="1d"):
        key = (sym, rng)
        if key not in self.cache:
            if self.offline is not None:
                if sym not in self.offline:
                    raise scan.ScanError("no offline chart for %s" % sym)
                self.cache[key] = self.offline[sym]
            else:
                self.cache[key] = scan.parse_chart(scan.yahoo_get(scan.chart_path(sym, rng, "5m")), sym)
                time.sleep(scan.PAUSE)
        return self.cache[key]

    def spark(self, symbols):
        if self.offline is not None:
            return {s: self.offline[s] for s in symbols if s in self.offline}
        data, _ = scan.fetch_spark(symbols, "1d", "5m", scan.PAUSE)
        return data


def bars_ohlc(series, day, cutoff):
    """Completed 5-minute bars of `day` at `cutoff`, with the open too (scan.session_bars has no open)."""
    bars = scan.session_bars(series, day, cutoff)
    opens = {}
    os_ = series.get("o") or []
    for i, ts in enumerate(series["t"]):
        if i < len(os_) and os_[i] is not None:
            opens[scan.ts_to_eastern(ts)] = float(os_[i])
    for b in bars:
        b["o"] = opens.get(b["start"], b["c"])
    return bars


def hhmm(text):
    return scan.parse_hhmm(text, "config")


def limits(cfg, day):
    """(last entry, flat by) as datetimes; on a 1:00 PM early close both move up with the close."""
    s = scan.session(day)
    close_dt = datetime.datetime.combine(day, s[1] if s else scan.CLOSE)
    last = min(datetime.datetime.combine(day, hhmm(cfg["no_entries_after"])), close_dt - 6 * BAR)
    flat = min(datetime.datetime.combine(day, hhmm(cfg["flat_by"])), close_dt - BAR)
    return last, flat


# ---------------------------------------------------------------- prepare: today's liquid list

def prepare(book, market, day, out=print):
    if market.offline is not None:
        syms = sorted(market.offline)
        book._write(book.liquid_path, {"day": day.isoformat(), "symbols": syms})
        return syms
    upath = os.path.join(ROOT, scan.DEFAULT_UNIVERSE) if not os.path.exists(scan.DEFAULT_UNIVERSE) else scan.DEFAULT_UNIVERSE
    if not os.path.exists(upath):
        raise PaperError("no trader/universe.txt: run `python3 trader-scanner/scan.py universe` first")
    universe = scan.symbols_from_file(upath)
    out("Ranking %d stocks by dollars traded (Yahoo spark, %d requests)..." % (len(universe), math.ceil(len(universe) / 20.0)))
    data, failed = scan.fetch_spark(universe, "5d", "1d", scan.PAUSE)
    ranked = []
    for s, ser in data.items():
        meta = ser.get("meta") or {}
        px, vol = meta.get("regularMarketPrice"), meta.get("regularMarketVolume")
        if px is None or vol is None or px < book.cfg["min_price"]:
            continue
        ranked.append((px * vol, s))
    ranked.sort(reverse=True)
    syms = [s for _, s in ranked[:int(book.cfg["liquid_count"])]]
    if not syms:
        raise PaperError("Yahoo returned no usable quotes (%d failed)" % len(failed))
    book._write(book.liquid_path, {"day": day.isoformat(), "symbols": syms})
    out("Kept the %d most traded: %s ..." % (len(syms), ", ".join(syms[:12])))
    return syms


def liquid_list(book, market, day, out=print):
    if os.path.exists(book.liquid_path):
        with open(book.liquid_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("day") == day.isoformat() and doc.get("symbols"):
            return doc["symbols"]
    return prepare(book, market, day, out)


# ---------------------------------------------------------------- exits

def manage(book, market, now_et, out=print):
    day, cutoff = now_et.date(), now_et.replace(second=0, microsecond=0)
    still = []
    for p in book.acct["positions"]:
        pday = datetime.date.fromisoformat(p["day"])
        try:
            ser = market.chart(p["symbol"], "1d" if pday == day else "5d")
        except scan.ScanError as e:
            out("  %s: could not read the chart (%s); holding, will check again" % (p["symbol"], e))
            still.append(p)
            continue
        flat_dt = limits(book.cfg, pday)[1]
        end = min(cutoff, flat_dt) if pday == day else flat_dt
        entered = datetime.datetime.fromisoformat(p["entered_at"])
        bars = [b for b in bars_ohlc(ser, pday, end) if b["start"] >= entered]
        done = None
        for b in bars:
            if b["l"] is not None and b["l"] <= p["stop"]:
                done = (min(p["stop"], b["o"]), "stop", b["start"] + BAR)
                break
            if b["h"] is not None and b["h"] >= p["target"]:
                done = (max(p["target"], b["o"]), "target", b["start"] + BAR)
                break
        if done is None and (pday < day or cutoff >= flat_dt):
            last = bars_ohlc(ser, pday, flat_dt)
            if last:
                done = (last[-1]["c"], "flat by %s" % scan.clock_label(flat_dt), last[-1]["start"] + BAR)
        if done is None:
            px = bars[-1]["c"] if bars else p["entry"]
            out("  HOLD %s %d sh  entry $%.2f  last $%.2f  stop $%.2f  target $%.2f  open P/L $%+.2f"
                % (p["symbol"], p["shares"], p["entry"], px, p["stop"], p["target"], (px - p["entry"]) * p["shares"]))
            still.append(p)
            continue
        fill, why, at = done
        fill = round(fill, 2)
        pnl = round((fill - p["entry"]) * p["shares"], 2)
        book.acct["cash"] = round(book.acct["cash"] + fill * p["shares"], 2)
        rec = dict(p, exit=fill, exited_at=at.isoformat(), reason=why, pnl=pnl)
        book.acct["closed"].append(rec)
        book.log({"event": "sell", "at": at.isoformat(), "symbol": p["symbol"], "shares": p["shares"],
                  "price": fill, "reason": why, "pnl": pnl})
        out("  SELL %s %d sh at $%.2f (%s, %s ET)  P/L $%+.2f" % (p["symbol"], p["shares"], fill, why,
                                                               scan.clock_label(at), pnl))
    book.acct["positions"] = still


# ---------------------------------------------------------------- entries

def look_for_entry(book, market, now_et, out=print):
    cfg = book.cfg
    day, cutoff = now_et.date(), now_et.replace(second=0, microsecond=0)
    t = cutoff.time()
    if t < hhmm(cfg["no_entries_before"]):
        return out("  No entries before %s ET." % cfg["no_entries_before"])
    last_entry = limits(cfg, day)[0]
    if cutoff > last_entry:
        return out("  No new entries after %s ET." % scan.clock_label(last_entry))
    entered, pnl = book.today(day)
    if len(entered) >= int(cfg["max_trades_per_day"]):
        return out("  Done for the day: %d of %d trades taken." % (len(entered), cfg["max_trades_per_day"]))
    if pnl <= -float(cfg["max_daily_loss_usd"]):
        return out("  Done for the day: down $%.2f, the daily loss limit is $%.0f." % (-pnl, cfg["max_daily_loss_usd"]))
    if len(book.acct["positions"]) >= int(cfg["max_open"]):
        return
    room = float(cfg["max_daily_loss_usd"]) + pnl  # what is left of today's loss limit
    max_loss = min(float(cfg["max_loss_per_trade_usd"]), room)
    taken = set(p["symbol"] for p in entered)
    syms = [s for s in liquid_list(book, market, day, out) if s not in taken]
    if not syms:
        return out("  Nothing left to scan.")
    stage1 = market.spark(syms)
    hits, counts, failed = scan.scan_orb(stage1, syms, day, cutoff, int(cfg["or_minutes"]),
                                         min_price=float(cfg["min_price"]),
                                         confirm=lambda s: market.chart(s), max_confirm=int(cfg["max_confirm"]))
    fresh_after = cutoff - BAR * (int(cfg["fresh_bars"]) + 1)
    picks = []
    for h in hits:
        trig = datetime.datetime.combine(day, hhmm(h["bar_start"]))
        if trig < fresh_after:
            continue  # a late entry is a different trade
        bars = bars_ohlc(market.chart(h["symbol"]), day, cutoff)
        last = bars[-1]
        if last["c"] <= h["or_high"]:
            continue  # fell back into the range
        dollars = sum(b["v"] for b in bars) * last["c"]
        picks.append((dollars, h, last))
    out("  Scanned %d charts: %d breakouts today, %d fresh." % (counts.get("scanned", 0), len(hits), len(picks)))
    if not picks:
        return
    picks.sort(key=lambda x: -x[0])
    for _, h, last in picks:
        try:
            plan = exitp.compute(last["c"], "or_mid", None, "r", exitp.D(cfg["target_r"]),
                                 or_high=h["or_high"], or_low=h["or_low"])
        except exitp.PlanError as e:
            out("  skip %s: %s" % (h["symbol"], e))
            continue
        entry, stop, target, risk = (float(plan[k]) for k in ("entry", "stop", "target", "risk"))
        shares = int(math.floor(max_loss / risk))
        shares = min(shares, int(math.floor(book.acct["cash"] / entry)))
        if shares < 1:
            out("  skip %s: one share risks $%.2f, over the $%.2f allowed" % (h["symbol"], risk, max_loss))
            continue
        at = last["start"] + BAR
        pos = {"symbol": h["symbol"], "day": day.isoformat(), "shares": shares, "entry": entry, "stop": stop,
               "target": target, "risk_per_share": risk, "entered_at": at.isoformat(),
               "or_high": h["or_high"], "or_low": h["or_low"], "trigger": h["at"]}
        book.acct["cash"] = round(book.acct["cash"] - entry * shares, 2)
        book.acct["positions"].append(pos)
        book.log(dict({"event": "buy", "at": at.isoformat(), "price": entry}, **pos))
        out("  BUY  %s %d sh at $%.2f (%s ET)  stop $%.2f  target $%.2f  risk $%.2f  [breakout %s, range %.2f-%.2f]"
            % (h["symbol"], shares, entry, scan.clock_label(at), stop, target, risk * shares, h["at"],
               h["or_low"], h["or_high"]))
        return pos


# ---------------------------------------------------------------- commands

def now_et(a):
    return scan.to_eastern(scan.parse_now(a.now))


def tick(book, market, now, out=print):
    out("%s ET  paper tick (simulated money)" % now.strftime("%a %Y-%m-%d %H:%M"))
    ok, why = scan.trading_day(now.date())
    if book.acct["positions"]:
        manage(book, market, now, out)
    if not ok:
        out("  Market closed (%s)." % why)
    else:
        s = scan.session(now.date())
        if scan.OPEN <= now.time() < s[1]:
            look_for_entry(book, market, now, out)
        else:
            out("  Outside market hours.")
    book.save()
    status(book, now, out, short=True)


def status(book, now, out=print, short=False):
    a = book.acct
    entered, pnl = book.today(now.date())
    total = round(sum(p["pnl"] for p in a["closed"]), 2)
    held = sum(p["entry"] * p["shares"] for p in a["positions"])
    out("  Cash $%.2f%s | today: %d trade(s), realized $%+.2f | all time: %d closed, $%+.2f (start $%.2f)"
        % (a["cash"], " + $%.2f in %s" % (held, ", ".join(p["symbol"] for p in a["positions"])) if held else "",
           len(entered), pnl, len(a["closed"]), total, a["starting_cash"]))
    if not short:
        for p in a["closed"][-10:]:
            out("    %s %s %d sh  $%.2f -> $%.2f  %s  $%+.2f" % (p["day"], p["symbol"], p["shares"], p["entry"],
                                                              p["exit"], p["reason"], p["pnl"]))
        wins = [p for p in a["closed"] if p["pnl"] > 0]
        if a["closed"]:
            out("  Win rate %d of %d. Simulated fills, no spread or slippage. Not financial advice."
                % (len(wins), len(a["closed"])))


def run(book, market, a):
    """Tick just after every 5-minute bar closes, until the session ends."""
    while True:
        now = now_et(a)
        s = scan.session(now.date())
        if s is None:
            print("Market closed today (%s). Nothing to run." % scan.trading_day(now.date())[1])
            return 0
        close_dt = datetime.datetime.combine(now.date(), s[1])
        first = datetime.datetime.combine(now.date(), hhmm(book.cfg["no_entries_before"]))
        if now >= close_dt:
            if book.acct["positions"]:
                tick(book, market, now)
            print("Session over.")
            status(book, now)
            return 0
        if now >= first or book.acct["positions"]:
            try:
                tick(book, market, now)
            except (scan.ScanError, PaperError, OSError, ValueError) as e:
                print("  tick failed: %s (will try the next bar)" % e)
            market.cache.clear()
        sys.stdout.flush()
        nxt = max(first, now.replace(second=0, microsecond=0) - datetime.timedelta(minutes=now.minute % 5) + BAR)
        nxt += datetime.timedelta(seconds=LAG)
        time.sleep(max(5.0, (nxt - now_et(a)).total_seconds()))


def main(argv=None):
    p = argparse.ArgumentParser(description="Automatic paper simulator (simulated money, no broker).")
    p.add_argument("cmd", choices=["prepare", "tick", "run", "status", "reset"])
    p.add_argument("--dir", default="trader/paper")
    p.add_argument("--now", help='replay time, New York, like "2026-10-19 10:15"')
    p.add_argument("--offline", help="saved Yahoo v8 chart(s), as in trader-scanner")
    a = p.parse_args(argv)
    book = Book(a.dir)
    try:
        market = Market(a.offline)
        if a.cmd == "reset":
            book.acct = book.fresh()
            book.save()
            print("Reset: $%.2f simulated cash, no positions." % book.acct["cash"])
        elif a.cmd == "prepare":
            prepare(book, market, now_et(a).date())
        elif a.cmd == "tick":
            tick(book, market, now_et(a))
        elif a.cmd == "status":
            status(book, now_et(a))
        elif a.cmd == "run":
            if a.now or a.offline:
                raise PaperError("run follows the live clock; replay a day with repeated `tick --now`")
            return run(book, market, a)
    except (scan.ScanError, PaperError) as e:
        print("paper.py: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
