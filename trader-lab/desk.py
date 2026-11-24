#!/usr/bin/env python3
"""Trader Desk: one morning report that runs the lab's research and the skills together.

    python3 trader-lab/desk.py                     # the 40-name lab universe
    python3 trader-lab/desk.py --tickers NVDA,AAPL --plan NVDA
    python3 trader-lab/desk.py --json

It calls the other skills' own scripts (scanner, news, pelosi, exit, budget, risk) and reads the
lab's results files; it re-implements none of them and never places an order. Every idea is shown
with the label its evidence earned in trader-lab/RESEARCH.md:
  PASS            cleared every pre-registered gate (none so far)
  FORWARD-TEST    frozen and being scored on new days only
  FAIL            failed its test; shown for context only
A part that cannot run (no network to a host, a missing file) shows "unavailable" and the rest goes on.
Research, not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAB = HERE
RESULTS = os.path.join(LAB, "results")
sys.path.insert(0, LAB)

DEFAULT_TICKERS = None   # filled from lab.UNIVERSE at run time

# What the lab learned about each scanner setup family (RESEARCH.md); the scanner's own names.
SETUP_EVIDENCE = {
    "breakout_20d": ("FAIL", "20-day breakout (Donchian/Turtle family): failed after costs on 30 years of daily bars"),
    "bull_flag": ("UNTESTED", "bull flag: not testable as a clean rule in the lab"),
    "reclaim_ma20": ("UNTESTED", "reclaim of the 20-day average: not tested on its own"),
    "oversold": ("FAIL", "RSI(14) under 30 dip-buying: indistinguishable from random entries (audit); faded after 2014"),
    "oversold_bounce": ("FAIL", "oversold bounce (dip-buying family): no edge beyond market exposure (audit, swarm)"),
}


def run(cmd, timeout=240):
    """Run a sibling script; return (parsed JSON or None, error text or None)."""
    try:
        p = subprocess.run([sys.executable] + cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timed out"
    out = p.stdout.strip()
    if out:
        try:
            return json.loads(out), None
        except ValueError:
            pass
    err = (p.stderr or p.stdout or "").strip().splitlines()
    return None, (err[-1] if err else "exit code %d" % p.returncode)[:200]


# ---------------------------------------------------------------- sections

def investing():
    path = os.path.join(LAB, "INVESTING-PLAN.md")
    if not os.path.exists(path):
        return {"error": "INVESTING-PLAN.md not found"}
    today = datetime.date.today()
    first_next = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    return {"plan": "the same amount into one broad, low-cost index ETF (e.g. VT or SPY/VOO/IVV) on the same day "
                    "every month; no timing, no selling in drops; dividends reinvested",
            "next_buy_month": first_next.strftime("%B %Y") if today.day > 1 else today.strftime("%B %Y"),
            "source": "trader-lab/INVESTING-PLAN.md"}


def market():
    try:
        import alloc
        import daily
        D = alloc.parse_adj(daily.fetch_daily("SPY"))
    except Exception as e:  # noqa: BLE001  (network or data: report, don't crash)
        return {"error": "SPY data unavailable: %s" % e}
    c = D["c"]
    if len(c) < 260:
        return {"error": "not enough SPY history"}
    sma200 = sum(c[-200:]) / 200
    rets = [c[i] / c[i - 1] - 1 for i in range(len(c) - 252, len(c))]
    vol20 = statistics.pstdev(rets[-20:]) * math.sqrt(252)
    vols = [statistics.pstdev(rets[i - 20:i]) * math.sqrt(252) for i in range(20, len(rets) + 1)]
    return {"date": D["d"][-1], "spy": round(c[-1], 2), "day_pct": round(100 * (c[-1] / c[-2] - 1), 2),
            "vs_200d_pct": round(100 * (c[-1] / sma200 - 1), 1), "trend": "above" if c[-1] > sma200 else "below",
            "vol20_pct": round(100 * vol20, 1), "vol_1y_median_pct": round(100 * statistics.median(vols), 1),
            "note": "context only: no timing rule on SPY beat holding it after 2009 (alloc.py)"}


def _load(name):
    p = os.path.join(RESULTS, name)
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def scoreboard():
    rows = []

    def add(name, verdict, detail):
        rows.append({"study": name, "verdict": verdict, "detail": detail})
    j = _load("latest.json")
    if j:
        kept = [c["strategy"] for c in j.get("chosen", []) if c.get("keep")]
        add("5-minute strategies (lab.py, 40 names)", "PASS" if kept else "FAIL",
            "kept: %s" % (", ".join(kept) if kept else "none (needs OOS t >= 3)"))
    j = _load("daily-latest.json")
    if j:
        passed = [c.get("rule") for c in j.get("chosen", []) if c.get("pass")]
        # R3 passed on today's 40 names but failed its pre-registered survivorship test on 110 fresh ETFs
        # (RESEARCH.md 2026-11-23, r3_etfs.py), so it is unproven, not a pass.
        unproven = [r for r in passed if "r3" in str(r).lower()]
        clean = [r for r in passed if r not in unproven]
        if clean:
            add("daily rules (daily.py, 30 years)", "PASS", "passed: %s" % ", ".join(map(str, clean)))
        if unproven:
            add("daily rule R3 (Connors, dip-buying)", "UNPROVEN",
                "passed on 40 survivor stocks, FAILED on 110 fresh ETFs (r3_etfs.py)")
        if not passed:
            add("daily rules (daily.py, 30 years)", "FAIL", "passed: none")
    j = _load("frozen.json")
    if j:
        n = len(j.get("rules", j)) if isinstance(j, dict) else len(j)
        add("frozen near-misses (daily.py forward)", "FORWARD-TEST", "%s rules scored on new days only" % n)
    for fname, label in (("orb-ema.json", "video strategy: ORB + 20 EMA pullback"),
                         ("long-3etf.json", "5-minute rules on 4 years SPY/QQQ/IWM")):
        j = _load(fname)
        if j:
            v = (j.get("chosen") or {}).get("verdict") if isinstance(j.get("chosen"), dict) else None
            if v is None:
                v = "PASS" if any(c.get("keep") for c in j.get("chosen", [])) else "FAIL"
            add(label, v, fname)
    for fname, label in (("alloc.json", "monthly trend/momentum/vol-targeting"),
                         ("vrp.json", "short volatility (SVXY contango)"),
                         ("parity.json", "risk parity / equal weight")):
        j = _load(fname)
        if j:
            vs = {k: r.get("verdict") for k, r in j.get("rules", {}).items()}
            add(label, "PASS" if "PASS" in vs.values() else "FAIL", ", ".join("%s %s" % kv for kv in vs.items()))
    j = _load("swarm.json")
    if j:
        add("swarm: 100,000 machine-made rules", "FAIL",
            "the 2 holdout 'passes' were a scoring artifact (RESEARCH.md 2026-11-24)")
    j = _load("sip-long.json")
    if j:
        v = j.get("verdict", {})
        add("stocks in play / end-of-day reversal, 40 names x 4 years",
            "PASS" if "PASS" in v.values() else "FAIL", json.dumps(v))
    any_pass = any(r["verdict"] == "PASS" for r in rows)
    return {"rows": rows, "any_pass": any_pass,
            "bottom_line": ("a rule passed: see its row" if any_pass else
                            "no rule has a proven edge after costs: trading stays on paper")}


def news(tickers, hours):
    args = ["trader-news/news.py", "--tickers"] + tickers + ["--hours", str(hours), "--json"]
    j, err = run(args + ["--no-write"] if False else args)
    if j is None and err and "User-Agent" in err:
        j, err = run(args + ["--no-sec"])
    if j is None:
        j, err = run(args + ["--no-sec"])
    if j is None:
        return {"error": err}
    moving = [m for m in j.get("moves", []) if m.get("moving")]
    per = {}
    for it in j.get("items", []):
        t = it.get("ticker")
        if not t:
            continue
        d = per.setdefault(t, {"headlines": 0, "tags": set(), "filings": []})
        if it.get("kind") == "headline":
            d["headlines"] += 1
        for tag in it.get("tags", []) or []:
            d["tags"].add(tag)
        if it.get("kind") == "filing" or it.get("form"):
            d["filings"].append(it.get("title", "")[:80])
    for d in per.values():
        d["tags"] = sorted(d["tags"])
    return {"moving": moving, "by_ticker": per, "sec": "on" if any(d["filings"] for d in per.values()) else "off"}


def congress():
    j, err = run(["trader-pelosi/ptr.py", "new", "--json"], timeout=120)
    if j is None:
        return {"error": err}
    rows = j if isinstance(j, list) else j.get("filings", j.get("rows", []))
    return {"new": rows[:20]}


def candidates(tickers, news_part):
    j, err = run(["trader-scanner/scan.py", "daily", "--symbols", ",".join(tickers), "--no-write", "--json"],
                 timeout=600)
    if j is None:
        return {"error": err}
    out = []
    by = (news_part or {}).get("by_ticker", {})
    moving = {m["ticker"]: m for m in (news_part or {}).get("moving", [])}
    for h in j.get("hits", []):
        s = h["symbol"]
        ev = [{"setup": st, "label": SETUP_EVIDENCE.get(st, ("UNTESTED", "not tested in the lab"))[0],
               "why": SETUP_EVIDENCE.get(st, ("", "not tested in the lab"))[1]} for st in h.get("setups", [])]
        out.append({"symbol": s, "price": h.get("price"), "rsi": h.get("rsi"), "setups": ev,
                    "news": by.get(s, {}), "moving_pct": moving.get(s, {}).get("pct")})
    out.sort(key=lambda r: (-(abs(r["moving_pct"] or 0)), -len(r["news"].get("tags", []))))
    return {"as_of": j.get("as_of"), "hits": out, "note": j.get("note")}


def trade_sheet(symbol, stop_pct, any_pass, budget=5000.0):
    """Paper ticket: exit plan -> size -> risk check. Never sends anything."""
    tmp = tempfile.mkdtemp(prefix="desk-")
    plan_p, orders_p = os.path.join(tmp, "plan.json"), os.path.join(tmp, "orders.json")
    quote, err = run(["trader-news/news.py", "--tickers", symbol, "--no-sec", "--hours", "1", "--json"], timeout=60)
    price = None
    for m in (quote or {}).get("moves", []):
        price = m.get("price")
    if not price:
        return {"error": "no price for %s (%s)" % (symbol, err)}
    plan, err = run(["trader-exit/exit.py", "plan", "--symbol", symbol, "--entry", str(price),
                     "--stop", "pct:%s" % stop_pct, "--write", plan_p, "--json"])
    if plan is None:
        return {"error": "exit plan: %s" % err}
    cfg_p = os.path.join(ROOT, "trader", "config.json")
    if not os.path.exists(cfg_p):            # paper defaults: the skills' own defaults plus this budget
        cfg_p = os.path.join(tmp, "config.json")
        with open(cfg_p, "w") as fh:
            json.dump({"budget": budget}, fh)
    size, err = run(["trader-budget/size.py", "--plan", plan_p, "--config", cfg_p, "--budget", str(budget),
                     "--write", orders_p, "--json"])
    if size is None:
        return {"error": "sizing: %s" % err, "plan": plan}
    size = size.get("sizing", size)
    risk, err = run(["trader-risk/check.py", "--orders", orders_p, "--config", cfg_p, "--no-write", "--json"])
    return {"symbol": symbol, "entry": price, "plan": plan, "size": size,
            "risk": risk if risk is not None else {"error": err},
            "mode": "LIVE-ELIGIBLE" if any_pass else "PAPER ONLY (no rule has a proven edge)"}


# ---------------------------------------------------------------- report

def build(a):
    import lab
    tickers = a.tickers or [s for s in lab.UNIVERSE]
    rep = {"created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "investing": investing(), "market": market(), "scoreboard": scoreboard()}
    rep["news"] = news(tickers, a.hours)
    rep["congress"] = congress()
    rep["candidates"] = candidates(tickers, rep["news"] if "error" not in rep["news"] else None)
    if a.plan:
        rep["trade_sheet"] = trade_sheet(a.plan, a.stop_pct, rep["scoreboard"]["any_pass"], a.budget)
    return rep


def text(rep):
    L = ["TRADER DESK  %s" % rep["created"], ""]
    inv = rep["investing"]
    L += ["1. INVESTING (the core)", "   " + inv.get("plan", inv.get("error", "")),
          "   next monthly buy: %s  (%s)" % (inv.get("next_buy_month", "-"), inv.get("source", "")), ""]
    m = rep["market"]
    L.append("2. MARKET")
    if "error" in m:
        L.append("   unavailable: " + m["error"])
    else:
        L.append("   SPY %.2f (%+.2f%% on %s), %s its 200-day average by %+.1f%%; 20-day vol %.1f%% vs 1-year median %.1f%%"
                 % (m["spy"], m["day_pct"], m["date"], m["trend"], m["vs_200d_pct"], m["vol20_pct"], m["vol_1y_median_pct"]))
        L.append("   " + m["note"])
    L += ["", "3. RESEARCH SCOREBOARD"]
    for r in rep["scoreboard"]["rows"]:
        L.append("   %-13s %-52s %s" % (r["verdict"], r["study"], r["detail"][:70]))
    L.append("   => " + rep["scoreboard"]["bottom_line"])
    L += ["", "4. NEWS RADAR"]
    n = rep["news"]
    if "error" in n:
        L.append("   unavailable: " + n["error"])
    else:
        for mv in n["moving"]:
            L.append("   MOVING %-5s %+.1f%%" % (mv["ticker"], mv["pct"]))
        tagged = {t: d for t, d in n["by_ticker"].items() if d["tags"] or d["filings"]}
        for t, d in sorted(tagged.items())[:15]:
            L.append("   %-5s tags: %s%s" % (t, ", ".join(d["tags"]) or "-", ("  8-K: " + d["filings"][0]) if d["filings"] else ""))
        if n.get("sec") == "off":
            L.append("   (SEC 8-K filings off: no SEC access or no sec_user_agent set)")
    c = rep["congress"]
    L.append("   Congress trades: " + ("unavailable: " + c["error"] if "error" in c else "%d new filings" % len(c["new"])))
    L += ["", "5. CANDIDATES (scanner hits, each with what the lab learned about its setup)"]
    cd = rep["candidates"]
    if "error" in cd:
        L.append("   unavailable: " + cd["error"])
    else:
        for h in cd["hits"][:15]:
            ev = "; ".join("%s=%s" % (e["setup"], e["label"]) for e in h["setups"])
            extra = []
            if h["moving_pct"] is not None:
                extra.append("moving %+.1f%%" % h["moving_pct"])
            if h["news"].get("tags"):
                extra.append("news: " + ",".join(h["news"]["tags"]))
            L.append("   %-5s %9.2f  %s  %s" % (h["symbol"], h["price"] or 0, ev, " | ".join(extra)))
        if not cd["hits"]:
            L.append("   no setups today")
        L.append("   " + (cd.get("note") or ""))
    if "trade_sheet" in rep:
        t = rep["trade_sheet"]
        L += ["", "6. TRADE SHEET (nothing is sent anywhere)"]
        if "error" in t:
            L.append("   unavailable: " + t["error"])
        else:
            pl = t["plan"]
            L.append("   %s entry %.2f  stop %s  target %s" % (t["symbol"], t["entry"], pl.get("stop"), pl.get("target")))
            sz = t["size"]
            L.append("   size: %s shares (%s), cost $%s, max loss at the stop $%s" % (
                sz.get("qty"), sz.get("bound_by", "-"), sz.get("cost"), sz.get("max_loss")))
            rk = t["risk"]
            res = (rk.get("results") or [{}])[0] if isinstance(rk, dict) else {}
            if res.get("verdict"):
                L.append("   risk check: %s%s" % (res["verdict"], ("  (" + "; ".join(res.get("reasons", []))[:150] + ")")
                                                  if res.get("reasons") else ""))
            else:
                L.append("   risk check: %s" % (rk.get("error") or json.dumps(rk)[:160]))
            L.append("   MODE: " + t["mode"])
    L += ["", "Research, not financial advice. A scan or a headline is not a reason to buy."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tickers", type=lambda s: [x.strip().upper() for x in s.split(",") if x.strip()])
    ap.add_argument("--hours", type=int, default=24, help="news window (default 24)")
    ap.add_argument("--plan", metavar="SYMBOL", help="build a paper trade sheet for this ticker")
    ap.add_argument("--stop-pct", type=float, default=2.0, help="stop distance for --plan (default 2%%)")
    ap.add_argument("--budget", type=float, default=5000.0, help="paper budget for --plan (default 5000)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rep = build(a)
    print(json.dumps(rep, indent=1, default=str) if a.json else text(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
