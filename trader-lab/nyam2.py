#!/usr/bin/env python3
"""NY AM Range Sweep, round 2: the indicator's own published rules (TradingView script OBursyFM). Pre-registered.

    python3 nyam2.py run [--write]   # data/candles (Tiingo crypto 5-minute bars) -> results/nyam2.json

Round 1 (nyam.py) guessed the details from a search summary. The script's page, read on 2026-11-26, says:
  "Session Range: Auto-plots the high/low of the 5:00-9:00 AM NY session."
  "The Sweep: Waits for a confirmed candle close beyond that range, not just a wick fake-out."
  "5-Min Confirmation: Requires a full engulfing candle (body and wick) in the direction of the move."
  "45-Min Confirmation: Cross-checks the higher timeframe before greenlighting the trade."
  "Dynamic stop loss tracking the true extreme of the move." "Take profit mapped to the opposite side of the AM range."
  "trade the other side of that trap" (a reversal), "Best used on: the 5-minute chart ... indices, forex, futures."
The source code is closed, so the 45-minute check and the signal window are still fixed here in advance.

PRE-REGISTERED 2026-11-26, committed before any result. Not to be changed:
  Markets: BTC/USD (primary), ETH/USD (reported): 24-hour 5-minute data is what the lab has; the stock store has
    regular hours only, so indices can't be tested on the pre-dawn range. Days as nyam.ny_days.
  Range: 05:00-08:55 New York high and low. Signals 09:00-11:55.
  Sweep: the first candle from 09:00 that closes beyond the range. One setup a day.
  Entry: after an up-sweep, the first FULL bearish engulfing candle (red; its high >= the previous high, its low <=
    the previous low, and its body covers the previous body) that also passes the 45-minute check -> short at its
    close. Mirror after a down-sweep.
  45-minute check: the last completed 45-minute candle (45-minute blocks from midnight New York) has the trade's
    colour (red for a short, green for a long).
  Stop: the extreme since the sweep began (the highest high for a short), updated up to entry, then fixed.
  Target: the opposite side of the AM range (the range low for a short). If entry is already past it, no trade.
  Stop wins a candle that touches both; anything open is closed at the 16:00 candle's open.
  Costs 20 bps a round trip; 10 bps reported.
  Split and verdict as round 1: in-sample before 2025-01-01, judged from 2025-01-01; PASS only if BTC judged t >= 3
    and in-sample mean > 0. Reported: $500 compounded on the judged years vs $500 held in BTC.
Research, not financial advice.
"""

import argparse
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nyam  # noqa: E402

RESULTS = os.path.join(HERE, "results")
BLOCK = 9           # 45 minutes of 5-minute candles
COST_BPS, REF_COST_BPS = 20.0, 10.0


def full_engulf(prev, cur, side):
    po, ph, pl, pc = prev
    co, ch, cl, cc = cur
    if ch < ph or cl > pl:
        return False
    if side > 0:
        return cc > co and co <= min(po, pc) and cc >= max(po, pc)
    return cc < co and co >= max(po, pc) and cc <= min(po, pc)


def last_45m_colour(b, s):
    """Colour (+1/-1/0) of the last 45-minute block completed before candle s closes."""
    end = ((s + 1) // BLOCK) * BLOCK          # first slot after the last complete block
    start = end - BLOCK
    if start < 0 or any(k not in b for k in range(start, end)):
        return 0
    o, c = b[start][0], b[end - 1][3]
    return 1 if c > o else (-1 if c < o else 0)


def day_trade(b):
    hi = max(b[s][1] for s in range(nyam.RANGE_FROM, nyam.RANGE_TO))
    lo = min(b[s][2] for s in range(nyam.RANGE_FROM, nyam.RANGE_TO))
    brk = None
    for s in range(nyam.RANGE_TO, nyam.SIGNAL_TO):
        c = b[s][3]
        if c > hi or c < lo:
            brk, up = s, c > hi
            break
    if brk is None:
        return None
    side = -1 if up else 1
    ext = b[brk][1] if up else b[brk][2]
    for s in range(brk + 1, nyam.SIGNAL_TO):
        ext = max(ext, b[s][1]) if up else min(ext, b[s][2])
        if not full_engulf(b[s - 1], b[s], side) or last_45m_colour(b, s) != side:
            continue
        e = b[s][3]
        stop, target = ext, (lo if up else hi)
        if (side < 0 and e <= target) or (side > 0 and e >= target) or abs(e - stop) <= 0:
            return None
        for j in range(s + 1, nyam.CLOSE_SLOT):
            o, h, l, _ = b[j]
            if (side > 0 and l <= stop) or (side < 0 and h >= stop):
                return side, e, (min(o, stop) if side > 0 else max(o, stop)), "stop"
            if (side > 0 and h >= target) or (side < 0 and l <= target):
                return side, e, (max(o, target) if side > 0 else min(o, target)), "target"
        return side, e, b[nyam.CLOSE_SLOT][0], "close"
    return None


def run_coin(days, cost):
    out = []
    for d, b in days.items():
        t = day_trade(b)
        if t:
            side, e, x, why = t
            out.append({"date": d, "ret": side * (x / e - 1) - cost / 1e4, "why": why})
    return out


def cmd_run(a):
    res = {"coins": {}}
    for coin in nyam.COINS:
        days = nyam.ny_days(coin)
        tr, ref = run_coin(days, COST_BPS), run_coin(days, REF_COST_BPS)
        s = {"in_sample": nyam.summary(tr, hi=nyam.SPLIT), "judged": nyam.summary(tr, lo=nyam.SPLIT),
             "judged_10bp_bps": nyam.summary(ref, lo=nyam.SPLIT)["bps"], "hold_usd_judged": nyam.hold_usd(coin, nyam.SPLIT),
             "days": len(days)}
        res["coins"][coin] = s
        print("%s | IS %3d tr %+6.1f bp t %+5.2f win %3.0f%% | judged %3d tr %+6.1f bp t %+5.2f win %3.0f%% (10bp %+.1f) "
              "| exits %s | $500 -> $%.0f (held $%.0f)" % (
                  coin, s["in_sample"]["trades"], s["in_sample"]["bps"], s["in_sample"]["t"],
                  100 * (s["in_sample"]["win_rate"] or 0), s["judged"]["trades"], s["judged"]["bps"], s["judged"]["t"],
                  100 * (s["judged"]["win_rate"] or 0), s["judged_10bp_bps"], s["judged"]["exits"], s["judged"]["usd"],
                  s["hold_usd_judged"] or 0))
    b = res["coins"]["btcusd"]
    res["verdict"] = "PASS" if (b["judged"]["t"] >= nyam.T_BAR and b["in_sample"]["bps"] > 0) else "FAIL"
    print("verdict (BTC):", res["verdict"])
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "nyam2.json"))
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
