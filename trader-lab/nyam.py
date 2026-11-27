#!/usr/bin/env python3
"""The "NY AM range sweep" indicator (TradingView), pre-registered test on Bitcoin and Ether 5-minute bars.

    python3 nyam.py run [--write]   # uses data/candles (Tiingo crypto 5-minute bars) -> results/nyam.json

The owner asked to test "nyam, an indicator". The public description (TradingView "NY AM Range Sweep"): mark the
high and low of the 5:00-9:00 AM New York session; a signal comes only after a candle closes beyond that range,
a 5-minute engulfing candle confirms, and a 45-minute check agrees; it then plots entry, stop and target. The
page itself couldn't be read (host not on the network allowlist), so the details below are fixed in advance
from that description, in both readings of "sweep". Crypto trades 24 hours, so the pre-dawn range exists in
the data; the stock store has regular hours only.

PRE-REGISTERED 2026-11-26, committed before any result. Not to be changed:
  Markets: BTC/USD (primary) and ETH/USD (reported) 5-minute bars, New York time (DST handled), weekdays only;
    a day counts only if every candle from 05:00 to 16:00 is present.
  Range: high and low of the 05:00-08:55 candles. Signals only from 09:00 to 11:55 (the NY AM session).
  Break: the first candle from 09:00 whose close is beyond the range (above the high: "up"; below the low: "down").
    One setup a day.
  Two readings, both tested:
    reversal (ICT "sweep"): after an up-break, the first bearish engulfing candle (red, body covers the previous
      candle's body) that closes back below the range high -> short at its close; stop = highest high since the
      break; mirror for a down-break.
    continuation: after an up-break, the first bullish engulfing candle (green, body covers the previous body)
      that closes above the range high -> long at its close; stop = the low of the two engulfing candles; mirror.
  45-minute check: the trade's direction must agree with the last 45 minutes: close at entry vs the close 9 candles
    earlier (higher for a long, lower for a short).
  Target 2R. Stop wins a candle that touches both. Anything open is closed at the 16:00 candle's open.
  Costs 20 bps a round trip (retail crypto taker fees and spread); 10 bps reported.
  Split: in-sample before 2025-01-01, judged from 2025-01-01.
  Verdict: a reading PASSES only if, on BTC, judged per-trade t >= 3 and the in-sample mean is positive.
  Reported: $500 compounded on the judged years, putting the whole $500 into each trade, next to $500 held in BTC.
Research, not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import candles  # noqa: E402
import lab  # noqa: E402

RESULTS = os.path.join(HERE, "results")
COINS = ["btcusd", "ethusd"]
RANGE_FROM, RANGE_TO = 5 * 12, 9 * 12          # slots of 5 minutes since midnight: 05:00 to 08:55
SIGNAL_TO = 12 * 12                            # signals until 11:55
CLOSE_SLOT = 16 * 12                           # 16:00
CHECK_BARS = 9                                 # 45 minutes
TARGET_R = 2.0
COST_BPS, REF_COST_BPS = 20.0, 10.0
SPLIT, T_BAR = "2025-01-01", 3.0
READINGS = ["reversal", "continuation"]


def ny_days(coin):
    """{date: {slot: (o, h, l, c)}} in New York time, weekdays with every 05:00-16:00 candle present."""
    bars = candles.load_gz(os.path.join(candles.STORE, coin + ".json.gz")) or {}
    days = {}
    for k, v in bars.items():
        loc = lab.to_eastern(lab.utc_of(int(k)))
        if loc.weekday() >= 5:
            continue
        days.setdefault(loc.date().isoformat(), {})[(loc.hour * 60 + loc.minute) // 5] = tuple(v[:4])
    return {d: b for d, b in sorted(days.items()) if all(s in b for s in range(RANGE_FROM, CLOSE_SLOT + 1))}


def engulf(prev, cur, side):
    """Cur's body covers prev's body, in colour `side` (+1 green, -1 red)."""
    po, pc, co, cc = prev[0], prev[3], cur[0], cur[3]
    if side > 0:
        return cc > co and co <= min(po, pc) and cc >= max(po, pc)
    return cc < co and co >= max(po, pc) and cc <= min(po, pc)


def day_trade(b, reading):
    """(side, entry, exit, why) or None for one New York day of candles `b` (slot -> ohlc)."""
    hi = max(b[s][1] for s in range(RANGE_FROM, RANGE_TO))
    lo = min(b[s][2] for s in range(RANGE_FROM, RANGE_TO))
    brk = None
    for s in range(RANGE_TO, SIGNAL_TO):
        c = b[s][3]
        if c > hi or c < lo:
            brk, up = s, c > hi
            break
    if brk is None:
        return None
    side = (-1 if up else 1) if reading == "reversal" else (1 if up else -1)
    ext = b[brk][1] if up else b[brk][2]       # the sweep's extreme so far
    for s in range(brk + 1, SIGNAL_TO):
        ext = max(ext, b[s][1]) if up else min(ext, b[s][2])
        cur, prev = b[s], b[s - 1]
        if not engulf(prev, cur, side):
            continue
        c = cur[3]
        if reading == "reversal":
            if (up and c >= hi) or (not up and c <= lo):
                continue
            stop = ext
        else:
            if (up and c <= hi) or (not up and c >= lo):
                continue
            stop = min(prev[2], cur[2]) if side > 0 else max(prev[1], cur[1])
        ref = b[s - CHECK_BARS][3]
        if (side > 0 and c <= ref) or (side < 0 and c >= ref):
            return None                          # the 45-minute check disagrees: no trade today
        risk = abs(c - stop)
        if risk <= 0:
            return None
        target = c + side * TARGET_R * risk
        for j in range(s + 1, CLOSE_SLOT):
            o, h, l, _ = b[j]
            if (side > 0 and l <= stop) or (side < 0 and h >= stop):
                return side, c, (min(o, stop) if side > 0 else max(o, stop)), "stop"
            if (side > 0 and h >= target) or (side < 0 and l <= target):
                return side, c, (max(o, target) if side > 0 else min(o, target)), "target"
        return side, c, b[CLOSE_SLOT][0], "close"
    return None


def tstat(x):
    if len(x) < 2:
        return 0.0
    sd = statistics.stdev(x)
    return statistics.mean(x) / (sd / math.sqrt(len(x))) if sd > 0 else 0.0


def run_coin(coin, reading, cost):
    out = []
    for d, b in ny_days(coin).items():
        t = day_trade(b, reading)
        if t:
            side, e, x, why = t
            out.append({"date": d, "side": side, "ret": side * (x / e - 1) - cost / 1e4, "why": why})
    return out


def summary(trades, lo=None, hi=None):
    x = [t["ret"] for t in trades if (lo is None or t["date"] >= lo) and (hi is None or t["date"] < hi)]
    ts = [t for t in trades if (lo is None or t["date"] >= lo) and (hi is None or t["date"] < hi)]
    usd = 500.0
    for r in x:
        usd *= 1 + r
    return {"trades": len(x), "bps": 1e4 * statistics.mean(x) if x else 0.0, "t": tstat(x),
            "win_rate": sum(r > 0 for r in x) / len(x) if x else None, "usd": usd,
            "exits": {w: sum(t["why"] == w for t in ts) for w in ("stop", "target", "close")}}


def hold_usd(coin, lo):
    days = ny_days(coin)
    ds = [d for d in days if d >= lo]
    if not ds:
        return None
    return 500.0 * days[ds[-1]][CLOSE_SLOT][0] / days[ds[0]][RANGE_FROM][0]


def cmd_run(a):
    res = {"coins": {}}
    for coin in COINS:
        days = ny_days(coin)
        res["coins"][coin] = {"days": len(days), "first": min(days) if days else None, "last": max(days) if days else None,
                              "hold_usd_judged": hold_usd(coin, SPLIT)}
        for reading in READINGS:
            tr = run_coin(coin, reading, COST_BPS)
            ref = run_coin(coin, reading, REF_COST_BPS)
            s = {"in_sample": summary(tr, hi=SPLIT), "judged": summary(tr, lo=SPLIT),
                 "judged_10bp_bps": summary(ref, lo=SPLIT)["bps"]}
            res["coins"][coin][reading] = s
            print("%s %-12s | IS %3d tr %+6.1f bp t %+5.2f win %3.0f%% | judged %3d tr %+6.1f bp t %+5.2f win %3.0f%% "
                  "(10bp: %+.1f) | $500 -> $%.0f" % (
                      coin, reading, s["in_sample"]["trades"], s["in_sample"]["bps"], s["in_sample"]["t"],
                      100 * (s["in_sample"]["win_rate"] or 0), s["judged"]["trades"], s["judged"]["bps"],
                      s["judged"]["t"], 100 * (s["judged"]["win_rate"] or 0), s["judged_10bp_bps"], s["judged"]["usd"]))
        print("%s: %d days %s..%s, held from 2025: $500 -> $%.0f" % (
            coin, len(days), res["coins"][coin]["first"], res["coins"][coin]["last"],
            res["coins"][coin]["hold_usd_judged"] or 0))
    btc = res["coins"]["btcusd"]
    res["verdict"] = {r: ("PASS" if btc[r]["judged"]["t"] >= T_BAR and btc[r]["in_sample"]["bps"] > 0 else "FAIL")
                      for r in READINGS}
    print("verdict (BTC):", res["verdict"])
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "nyam.json"))
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
