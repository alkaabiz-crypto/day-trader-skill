#!/usr/bin/env python3
"""trader-lab exness: what a trade really costs and risks on an Exness CFD account at its minimum lot.

    python3 exness.py table [--account 3000]              # every instrument: min-lot exposure, cost, leverage
    python3 exness.py check --symbol USTEC --price 25000 --stop 24800 [--lots 0.05] [--account 3000] [--max-loss 60]

Why: the rest of the pack sizes US stock orders in dollars. CFDs cannot be sized below the broker's minimum lot,
so on a small account the minimum lot, not the plan, sets the risk. This module answers: how big is one minimum lot
in dollars, what does a round trip cost in dollars and basis points, how much leverage does it put on the account,
and does the stop fit the loss limit. Every research script in research/exness-2026-11 used these numbers by hand.

The table below is the user's Exness Standard account (UAE, Extended Swap-Free: $0 swap, $0 commission, 1:200),
checked in the MT5 terminal on 2026-11-27 where marked "terminal"; other rows are unverified estimates.
Slippage is an assumption (1 point on the indices, $5 per BTC). Research, not financial advice. Never places orders.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request

# symbol: (min lot, units per lot (dollars per 1.0 price move per lot), spread in price units, slippage per round trip,
#          wider spread at the US cash open, Yahoo proxy for the price, source)
SPECS = {
    "USTEC":  dict(min_lot=0.05, per_lot=1.0, spread=1.12, slip=1.0, open_spread=3.5, proxy="^NDX", source="terminal"),
    "US500":  dict(min_lot=0.14, per_lot=1.0, spread=0.40, slip=0.5, open_spread=1.0, proxy="^GSPC", source="terminal"),
    "BTCUSD": dict(min_lot=0.01, per_lot=1.0, spread=6.40, slip=5.0, open_spread=6.40, proxy="BTC-USD", source="terminal"),
    "XAUUSD": dict(min_lot=0.01, per_lot=100.0, spread=0.20, slip=0.20, open_spread=0.40, proxy="GC=F", source="terminal"),
    "USOIL":  dict(min_lot=0.01, per_lot=1000.0, spread=0.03, slip=0.02, open_spread=0.05, proxy="CL=F", source="terminal lot; spread unverified"),
    "UKOIL":  dict(min_lot=0.01, per_lot=1000.0, spread=0.04, slip=0.02, open_spread=0.06, proxy="BZ=F", source="terminal lot; spread unverified"),
    "EURUSD": dict(min_lot=0.01, per_lot=100000.0, spread=0.00008, slip=0.00005, open_spread=0.00008, proxy="EURUSD=X", source="terminal lot; spread third-party"),
    "ETHUSD": dict(min_lot=0.1, per_lot=1.0, spread=1.5, slip=1.0, open_spread=1.5, proxy="ETH-USD", source="unverified"),
}
SWAP_FREE = True


def spec(symbol):
    s = symbol.upper()
    if s not in SPECS:
        raise KeyError("unknown Exness symbol %s (known: %s)" % (symbol, ", ".join(sorted(SPECS))))
    return SPECS[s]


def exposure_usd(symbol, price, lots=None):
    """Dollar value of the position (notional) at `lots` (default: the minimum lot)."""
    sp = spec(symbol)
    return price * sp["per_lot"] * (sp["min_lot"] if lots is None else lots)


def round_trip_usd(symbol, lots=None, at_open=False):
    """Dollars paid for one entry plus one exit: the full spread once plus slippage."""
    sp = spec(symbol)
    lots = sp["min_lot"] if lots is None else lots
    return ((sp["open_spread"] if at_open else sp["spread"]) + sp["slip"]) * sp["per_lot"] * lots


def round_trip_bps(symbol, price, at_open=False):
    sp = spec(symbol)
    return ((sp["open_spread"] if at_open else sp["spread"]) + sp["slip"]) / price * 1e4


def check(symbol, price, stop, lots=None, account=3000.0, max_loss=None, max_leverage=2.0):
    """Risk check for one CFD trade. Returns dict(ok, problems, numbers). A lot below the minimum is a problem,
    because the broker rejects it; a minimum lot whose stop loss exceeds the limit is a problem, because the
    position cannot be made smaller."""
    sp = spec(symbol)
    lots = sp["min_lot"] if lots is None else lots
    problems = []
    if lots < sp["min_lot"] - 1e-12:
        problems.append("%.2f lots is below the %s minimum of %.2f" % (lots, symbol, sp["min_lot"]))
    notional = exposure_usd(symbol, price, lots)
    loss = abs(price - stop) * sp["per_lot"] * lots + round_trip_usd(symbol, lots)
    lev = notional / account if account else float("inf")
    if max_loss is not None and loss > max_loss:
        problems.append("loss at the stop $%.2f is over the $%.2f limit%s" % (
            loss, max_loss, " and the minimum lot cannot be smaller" if abs(lots - sp["min_lot"]) < 1e-12 else ""))
    if lev > max_leverage:
        problems.append("position is %.1fx the account (limit %.1fx)" % (lev, max_leverage))
    return dict(ok=not problems, problems=problems, symbol=symbol.upper(), lots=lots, notional_usd=round(notional, 2),
                loss_at_stop_usd=round(loss, 2), leverage=round(lev, 2), cost_usd=round(round_trip_usd(symbol, lots), 2),
                cost_bps=round(round_trip_bps(symbol, price), 2), swap_free=SWAP_FREE, source=sp["source"])


def yahoo_price(sym):
    u = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=5d&interval=1d" % urllib.parse.quote(sym)
    r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20))
    closes = [c for c in r["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
    return closes[-1]


def table(account):
    print("Exness minimum lots on a $%.0f account (swap-free, $0 commission). Prices from Yahoo proxies." % account)
    print("%-7s %8s %12s %10s %9s %8s %8s  %s" % ("symbol", "min lot", "price", "exposure", "x acct", "cost $", "cost bp", "source"))
    for s, sp in SPECS.items():
        try:
            p = yahoo_price(sp["proxy"])
        except Exception as e:  # network blocked or symbol missing
            print("%-7s %8.2f  price unavailable (%s)" % (s, sp["min_lot"], e.__class__.__name__))
            continue
        x = exposure_usd(s, p)
        print("%-7s %8.2f %12.2f %10.0f %8.2fx %8.2f %8.2f  %s" % (s, sp["min_lot"], p, x, x / account, round_trip_usd(s),
                                                                   round_trip_bps(s, p), sp["source"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("table")
    p.add_argument("--account", type=float, default=3000.0)
    p = sub.add_parser("check")
    p.add_argument("--symbol", required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--lots", type=float)
    p.add_argument("--account", type=float, default=3000.0)
    p.add_argument("--max-loss", type=float)
    p.add_argument("--max-leverage", type=float, default=2.0)
    a = ap.parse_args(argv)
    if a.cmd == "table":
        table(a.account)
        return 0
    r = check(a.symbol, a.price, a.stop, a.lots, a.account, a.max_loss, a.max_leverage)
    print(json.dumps(r, indent=1))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
