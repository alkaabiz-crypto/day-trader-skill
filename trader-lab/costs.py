#!/usr/bin/env python3
"""trader-lab costs: estimate what a round trip really costs, and check a trade plan against it.

    python3 costs.py table                         # estimated spread per symbol (last 21 days)
    python3 costs.py check                         # trader/plan.json from trader-exit
    python3 costs.py check --symbol TSLA --entry 364.18 --stop 358.32 --target 370.04

The bid-ask spread is estimated from daily highs and lows with Corwin & Schultz (2012,
Journal of Finance), "A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low
Prices", with their overnight-gap adjustment, two-day estimates floored at zero, averaged
over the last 21 days. A round trip pays the full spread once plus slippage (default 1 bp a
side) and the SEC fee on the sale (about 0.3 bp). The check warns when costs eat more than 10%
of the planned reward or 20% of the planned risk. Research, not financial advice.
"""

import argparse
import json
import math
import os
import statistics
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402
import lab  # noqa: E402

SEC_FEE_BPS = 0.3
SLIP_BPS = 1.0
WARN_REWARD = 0.10
WARN_RISK = 0.20


def cs_spread(H, L, C):
    """Corwin-Schultz spread (fraction of price) for each 2-day window ending at index t>=1.
    Day t's high and low are shifted by the overnight gap when the previous close lies outside
    them (the paper's adjustment). Negative estimates are set to 0."""
    k = 3 - 2 * math.sqrt(2)
    out = [None]
    for t in range(1, len(H)):
        h1, l1 = H[t], L[t]
        pc = C[t - 1]
        if pc < l1:
            h1, l1 = h1 - (l1 - pc), pc
        elif pc > h1:
            h1, l1 = pc, l1 + (pc - h1)
        if min(L[t - 1], l1) <= 0 or l1 <= 0:
            out.append(None)
            continue
        beta = math.log(H[t - 1] / L[t - 1]) ** 2 + math.log(h1 / l1) ** 2
        gamma = math.log(max(H[t - 1], h1) / min(L[t - 1], l1)) ** 2
        alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / k - math.sqrt(gamma / k)
        s = 2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha))
        out.append(max(0.0, s))
    return out


def live_quote_bps(sym):
    """Live IEX top-of-book spread from Tiingo (the session's proxy supplies the key). None when
    the market is closed or the quote is missing."""
    try:
        req = urllib.request.Request("https://api.tiingo.com/iex/?tickers=%s" % sym,
                                     headers={"User-Agent": daily.UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            rows = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None, None
    for q in rows or []:
        b, a = q.get("bidPrice"), q.get("askPrice")
        if b and a and a > b > 0:
            return (a - b) / ((a + b) / 2) * 1e4, q.get("quoteTimestamp") or q.get("timestamp")
    return None, None


def spread_5min_bps(sym, sessions=5):
    """Median Corwin-Schultz estimate over consecutive 5-minute bars of the last full sessions
    (long store first, then the 60-day store). An upper bound for very liquid names."""
    for store in (lab.LONG_STORE, lab.STORE):
        if not os.path.exists(lab.store_path(sym, store)):
            continue
        ss = [(d, b) for d, b in lab.sessions_of(lab.load_store(sym, store)) if len(b) == lab.SESSION_BARS]
        est = []
        for _, b in ss[-sessions:]:
            est += [x for x in cs_spread([x["h"] for x in b], [x["l"] for x in b], [x["c"] for x in b])
                    if x is not None]
        if est:
            return statistics.median(est) * 1e4, ss[-1][0]
    return None, None


def spread_daily_bps(sym, days=21):
    D = daily.load(sym)
    if not D or len(D["d"]) < days + 2:
        return None, None
    s = [x for x in cs_spread(D["h"], D["l"], D["c"])[-days:] if x is not None]
    return (sum(s) / len(s) * 1e4 if s else None), D["d"][-1]


def spread_bps(sym, live=True):
    """-> (bps, as_of, source). Best source first: live quote, 5-minute estimate, daily estimate."""
    if live:
        sp, t = live_quote_bps(sym)
        if sp is not None:
            return sp, t, "live IEX quote"
    sp, t = spread_5min_bps(sym)
    if sp is not None:
        return sp, t, "5-min high-low estimate (upper bound for liquid names)"
    sp, t = spread_daily_bps(sym)
    if sp is not None:
        return sp, t, "daily high-low estimate (rough; overstates liquid names a lot)"
    return None, None, None


def round_trip_bps(spread, slip=SLIP_BPS):
    return spread + 2 * slip + SEC_FEE_BPS


def check(sym, entry, stop, target, slip=SLIP_BPS, live=True):
    sp, asof, source = spread_bps(sym, live)
    if sp is None:
        return {"symbol": sym, "error": "no quote or price data: run daily.py fetch --symbols %s" % sym}
    cost = round_trip_bps(sp, slip)
    reward = abs(target - entry) / entry * 1e4 if target else None
    risk = abs(entry - stop) / entry * 1e4 if stop else None
    warn = []
    if reward and cost > WARN_REWARD * reward:
        warn.append("costs are %.0f%% of the planned reward" % (100 * cost / reward))
    if risk and cost > WARN_RISK * risk:
        warn.append("costs are %.0f%% of the planned risk (the stop is too tight for this spread)" % (100 * cost / risk))
    return {"symbol": sym, "as_of": asof, "source": source, "spread_bps": round(sp, 2),
            "round_trip_bps": round(cost, 2),
            "reward_bps": round(reward, 1) if reward else None, "risk_bps": round(risk, 1) if risk else None,
            "net_reward_bps": round(reward - cost, 1) if reward else None, "warnings": warn}


def main(argv=None):
    ap = argparse.ArgumentParser(description="trader-lab cost estimator")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("table")
    p.add_argument("--symbols", type=lambda s: s.upper().split(","), default=daily.UNIVERSE)
    p = sub.add_parser("check")
    p.add_argument("--plan", default="trader/plan.json")
    p.add_argument("--symbol")
    p.add_argument("--entry", type=float)
    p.add_argument("--stop", type=float)
    p.add_argument("--target", type=float)
    p.add_argument("--slip", type=float, default=SLIP_BPS, help="slippage per side, bps (default 1)")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "table":
        print("%-6s %9s %11s   %-12s %s" % ("symbol", "spread bp", "round trip", "as of", "source"))
        for s in a.symbols:
            sp, asof, src = spread_bps(s)
            if sp is not None:
                print("%-6s %9.2f %11.2f   %-12s %s" % (s, sp, round_trip_bps(sp), str(asof)[:10], src))
        print("\nRound trip = spread + 1 bp slippage a side + SEC fee. High-low estimates (Corwin & Schultz")
        print("2012) cannot see spreads smaller than ordinary price noise; prefer the live quote.")
        return 0
    if a.cmd == "check":
        if a.symbol:
            sym, entry, stop, target = a.symbol.upper(), a.entry, a.stop, a.target
        else:
            if not os.path.exists(a.plan):
                print("costs.py: no %s; give --symbol --entry --stop --target" % a.plan, file=sys.stderr)
                return 1
            with open(a.plan) as fh:
                plan = json.load(fh)
            sym, entry, stop, target = plan["symbol"], plan["entry"], plan.get("stop"), plan.get("target")
        if not entry:
            print("costs.py: need an entry price", file=sys.stderr)
            return 1
        r = check(sym, entry, stop, target, a.slip)
        if a.json:
            print(json.dumps(r, indent=1))
            return 0
        if "error" in r:
            print("costs.py: %s" % r["error"], file=sys.stderr)
            return 1
        print("%s: spread %.2f bp, round trip %.2f bp (%s, %s)" % (
            r["symbol"], r["spread_bps"], r["round_trip_bps"], r["source"], r["as_of"]))
        if r["reward_bps"]:
            print("  planned reward %.1f bp, after costs %.1f bp" % (r["reward_bps"], r["net_reward_bps"]))
        if r["risk_bps"]:
            print("  planned risk %.1f bp" % r["risk_bps"])
        for w in r["warnings"]:
            print("  WARNING: " + w)
        if not r["warnings"]:
            print("  OK: costs are small next to this plan.")
        print("Estimate only; check the live quote at your broker. Not financial advice.")
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
