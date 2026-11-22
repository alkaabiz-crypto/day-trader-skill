#!/usr/bin/env python3
"""trader-lab hourly engine: time-of-day day-trading rules on ~3 years of hourly bars.

Yahoo serves 60-minute bars for the last 730 days: 9:30, 10:30, ... 14:30 and a final
15:30-16:00 half hour, 7 bars a session. That is enough to test the rules that only
need "the first hour", "the last half hour" or "lunch", on ~700 sessions instead of 60.

    python3 hourly.py fetch
    python3 hourly.py backtest [--write] [--only imom,rod] [--json]

Periods split by date: IS the first 50%, OOS the next 25%, HOLDOUT the last 25%.
Same gates as daily.py: IS t >= 2, OOS and HOLDOUT positive, t >= 3 after IS.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402  (stats, deflated Sharpe, universe)

STORE = os.path.join(HERE, "data", "hourly")
RESULTS = os.path.join(HERE, "results")
UNIVERSE = sorted(set(daily.UNIVERSE + ["PLTR", "COIN", "MSTR", "SMCI", "UBER", "SHOP", "CRWD", "CRM", "ARM"]))
COST_BPS = 2.0
BARS = 7


class LabError(Exception):
    pass


def to_eastern(utc):
    y = utc.year
    d = datetime.date(y, 3, 1)
    start = datetime.datetime.combine(d + datetime.timedelta(days=(6 - d.weekday()) % 7 + 7), datetime.time(7))
    d = datetime.date(y, 11, 1)
    end = datetime.datetime.combine(d + datetime.timedelta(days=(6 - d.weekday()) % 7), datetime.time(6))
    return utc - datetime.timedelta(hours=4 if start <= utc < end else 5)


def fetch(sym):
    url = "https://%s.finance.yahoo.com/v8/finance/chart/%s?range=730d&interval=60m"
    last = None
    for host in ("query2", "query1"):
        try:
            req = urllib.request.Request(url % (host, sym), headers={"User-Agent": daily.UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e.code
            time.sleep(2)
        except (urllib.error.URLError, OSError) as e:
            raise LabError("could not reach Yahoo: %s" % getattr(e, "reason", e))
    raise LabError("Yahoo answered HTTP %s for %s" % (last, sym))


def parse(text, now_utc=None):
    """-> {ts: [o,h,l,c,v]} for complete regular-session hourly bars (slot 0..6)."""
    res = ((json.loads(text).get("chart") or {}).get("result") or [None])[0]
    if not res:
        raise LabError("no data")
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    now = now_utc or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    out = {}
    for i, ts in enumerate(res.get("timestamp") or []):
        row = [(q.get(k) or [None] * (i + 1))[i] for k in ("open", "high", "low", "close", "volume")]
        if ts is None or None in row[:4]:
            continue
        start = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts))
        loc = to_eastern(start)
        m = loc.hour * 60 + loc.minute - (9 * 60 + 30)
        if m < 0 or m % 60 or m // 60 >= BARS:
            continue
        length = 30 if m // 60 == 6 else 60
        if start + datetime.timedelta(minutes=length) > now:
            continue
        out[str(int(ts))] = [float(x or 0) for x in row]
    return out


def load(sym, store=STORE):
    p = os.path.join(store, "%s.json.gz" % sym)
    if not os.path.exists(p):
        return {}
    with gzip.open(p, "rt") as fh:
        return json.load(fh)


def save(sym, bars, store=STORE):
    os.makedirs(store, exist_ok=True)
    with gzip.GzipFile(os.path.join(store, "%s.json.gz" % sym), "wb", mtime=0) as gz:
        gz.write(json.dumps({k: bars[k] for k in sorted(bars, key=int)}, separators=(",", ":")).encode())


def sessions(bars):
    """-> [(date, [7 bar dicts])] full sessions only, oldest first."""
    days = {}
    for ts, (o, h, l, c, v) in bars.items():
        loc = to_eastern(datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts)))
        slot = (loc.hour * 60 + loc.minute - 570) // 60
        days.setdefault(loc.date().isoformat(), {})[slot] = {"o": o, "h": h, "l": l, "c": c, "v": v}
    return [(d, [days[d][k] for k in range(BARS)]) for d in sorted(days) if len(days[d]) == BARS]


# ---------------------------------------------------------------- rules
# rule(S, k, ctx, p) -> list of trades [(side, entry, exit)] for session k; ctx has prev_close.

def at_close(side, e, x):
    return [(side, e, x)]


def h_imom(S, k, ctx, p):
    """Gao et al. 2018 with hourly bars: prev close -> 10:30 predicts 15:30 -> 16:00."""
    B, pc = S[k][1], ctx["pc"]
    r = B[0]["c"] / pc - 1
    if abs(r) * 1e4 < p["min"]:
        return []
    side = (1 if r > 0 else -1) * (1 if p["mode"] == "mom" else -1)
    return at_close(side, B[6]["o"], B[6]["c"])


def h_rod(S, k, ctx, p):
    """Baltussen et al. 2021: prev close -> 15:30 predicts 15:30 -> 16:00."""
    B, pc = S[k][1], ctx["pc"]
    r = B[5]["c"] / pc - 1
    if abs(r) * 1e4 < p["min"]:
        return []
    side = (1 if r > 0 else -1) * (1 if p["mode"] == "mom" else -1)
    return at_close(side, B[6]["o"], B[6]["c"])


def h_fhr(S, k, ctx, p):
    """First-hour move (open -> 10:30): follow or fade it from 10:30 to the close."""
    B = S[k][1]
    r = B[0]["c"] / B[0]["o"] - 1
    if abs(r) * 1e4 < p["min"]:
        return []
    side = (1 if r > 0 else -1) * (1 if p["mode"] == "mom" else -1)
    return at_close(side, B[1]["o"], B[6]["c"])


def h_orb60(S, k, ctx, p):
    """60-minute opening-range breakout: stop entry at the first hour's high (long) / low (short),
    stop-loss at the other side, out at the close. A bar that hits entry and stop counts as stopped."""
    B = S[k][1]
    hi, lo = B[0]["h"], B[0]["l"]
    green = B[0]["c"] > B[0]["o"]
    sides = [1, -1] if p["dir"] == "both" else ([1] if green else [-1])
    for j in range(1, BARS):
        b = B[j]
        for s in sides:
            if (s > 0 and b["h"] > hi) or (s < 0 and b["l"] < lo):
                e = max(hi, b["o"]) if s > 0 else min(lo, b["o"])
                sl = lo if s > 0 else hi
                if p["stop"] == "mid":
                    sl = (hi + lo) / 2.0
                if (s > 0 and b["l"] <= sl) or (s < 0 and b["h"] >= sl):
                    return [(s, e, sl)]
                for m in range(j + 1, BARS):
                    if (s > 0 and B[m]["l"] <= sl) or (s < 0 and B[m]["h"] >= sl):
                        return [(s, e, min(sl, B[m]["o"]) if s > 0 else max(sl, B[m]["o"]))]
                return [(s, e, B[6]["c"])]
    return []


def h_hour(S, k, ctx, p):
    """Seasonality control: long one hourly bar every day."""
    b = S[k][1][p["slot"]]
    return [(1, b["o"], b["c"])]


def h_lunch(S, k, ctx, p):
    """Quantpedia lunch effect, hourly version: long 12:30 -> 14:30."""
    B = S[k][1]
    return [(1, B[3]["o"], B[4]["c"])]


def h_gapfh(S, k, ctx, p):
    """Gap day: if the first hour moves against the gap (a fill starting), trade the fill direction
    from 10:30 to the close; if it extends the gap, trade the gap direction."""
    B, pc = S[k][1], ctx["pc"]
    g = B[0]["o"] / pc - 1
    if abs(g) * 100 < p["min"]:
        return []
    fh = B[0]["c"] / B[0]["o"] - 1
    side = 1 if fh > 0 else -1
    if (side > 0) == (g > 0) and p["mode"] == "fill":
        return []
    if (side > 0) != (g > 0) and p["mode"] == "extend":
        return []
    return at_close(side, B[1]["o"], B[6]["c"])


def grid(d):
    return daily.grid(d)


RULES = {
    "imom": {"fn": h_imom, "source": "Gao, Han, Li & Zhou 2018 JFE (hourly)",
             "grid": {"min": [0, 25, 50], "mode": ["mom", "rev"]}},
    "rod": {"fn": h_rod, "source": "Baltussen, Da, Lammers & Martens 2021 JFE",
            "grid": {"min": [0, 50, 100], "mode": ["mom", "rev"]}},
    "fhr": {"fn": h_fhr, "source": "first-hour momentum / reversal",
            "grid": {"min": [0, 50, 100], "mode": ["mom", "rev"]}},
    "orb60": {"fn": h_orb60, "source": "60-minute opening range breakout (Crabel; Fisher ACD)",
              "grid": {"dir": ["both", "candle"], "stop": ["range", "mid"]}},
    "hour": {"fn": h_hour, "source": "time-of-day seasonality control", "grid": {"slot": list(range(BARS))}},
    "lunch": {"fn": h_lunch, "source": "Quantpedia lunch effect", "grid": {"x": [1]}},
    "gapfh": {"fn": h_gapfh, "source": "gap + first hour: fill or extend",
              "grid": {"min": [0.5, 1.0], "mode": ["fill", "extend"]}},
}


def backtest(uni, cost=COST_BPS, only=None):
    dates = sorted({d for ss in uni.values() for d, _ in ss})
    if len(dates) < 100:
        raise LabError("only %d sessions; run fetch" % len(dates))
    c1, c2 = dates[len(dates) // 2], dates[(3 * len(dates)) // 4]
    part = lambda d: "is" if d < c1 else ("oos" if d < c2 else "ho")
    variants = []
    for name, spec in RULES.items():
        if only and name not in only:
            continue
        for p in grid(spec["grid"]):
            by_day, trades = {}, []
            for sym, ss in uni.items():
                for k in range(1, len(ss)):
                    if ss[k - 1][0] < ss[k][0]:
                        ctx = {"pc": ss[k - 1][1][-1]["c"]}
                        for side, e, x in spec["fn"](ss, k, ctx, p):
                            r = side * (x / e - 1) * 1e4 - cost
                            trades.append(r)
                            by_day.setdefault(ss[k][0], []).append(r)
            series = [(d, statistics.mean(by_day[d]) if d in by_day else 0.0) for d in dates]
            row = {"rule": name, "params": p, "source": spec["source"], "trades": len(trades),
                   "win": sum(1 for r in trades if r > 0) / len(trades) if trades else 0,
                   "avg_trade_bps": statistics.mean(trades) if trades else 0}
            for pt in ("is", "oos", "ho"):
                row[pt] = daily.stats([r for d, r in series if part(d) == pt])
            post = [r for d, r in series if part(d) != "is"]
            row["post"] = daily.stats(post)
            row["_post"] = post
            variants.append(row)
    srs = [v["oos"]["sharpe"] / math.sqrt(252) for v in variants]
    var = daily.robust_var(srs)
    for v in variants:
        v["dsr"] = daily.deflated_sharpe(v.pop("_post"), len(variants), var)
    best = {}
    for v in variants:
        if v["rule"] not in best or v["is"]["sharpe"] > best[v["rule"]]["is"]["sharpe"]:
            best[v["rule"]] = v
    chosen = []
    for name, v in best.items():
        ok = v["is"]["t"] >= daily.MIN_IS_T and v["oos"]["mean"] > 0 and v["ho"]["mean"] > 0 \
            and v["post"]["t"] >= daily.POST_T
        chosen.append({"rule": name, "params": v["params"], "pass": ok, "trades": v["trades"],
                       "win": v["win"], "avg_trade_bps": v["avg_trade_bps"], "is_t": v["is"]["t"],
                       "oos_sharpe": v["oos"]["sharpe"], "oos_t": v["oos"]["t"], "ho_sharpe": v["ho"]["sharpe"],
                       "ho_t": v["ho"]["t"], "post_t": v["post"]["t"], "dsr": v["dsr"], "source": v["source"]})
    chosen.sort(key=lambda c: (not c["pass"], -c["post_t"]))
    return {"dates": [dates[0], dates[-1]], "n_dates": len(dates), "cuts": [c1, c2], "cost_bps": cost,
            "n_variants": len(variants), "symbols": sorted(uni), "variants": variants, "chosen": chosen}


def report(res):
    L = ["Hourly engine: %d sessions %s to %s, %d symbols, %d variants, %.1f bps per trade." % (
        res["n_dates"], res["dates"][0], res["dates"][1], len(res["symbols"]), res["n_variants"], res["cost_bps"]),
        "IS before %s, OOS before %s, HOLDOUT after." % tuple(res["cuts"]), "",
        "%-6s %-26s %7s %5s %6s | %5s | %6s %6s | %6s %6s | %6s %5s" % (
            "rule", "params", "trades", "win", "avg bp", "IS t", "OOS Sh", "OOS t", "HO Sh", "HO t", "post t", "DSR"),
        "-" * 108]
    for c in res["chosen"]:
        p = ",".join("%s=%s" % kv for kv in sorted(c["params"].items()))
        L.append("%-6s %-26s %7d %4.0f%% %6.1f | %5.2f | %6.2f %6.2f | %6.2f %6.2f | %6.2f %5.3f %s" % (
            c["rule"], p[:26], c["trades"], c["win"] * 100, c["avg_trade_bps"], c["is_t"], c["oos_sharpe"],
            c["oos_t"], c["ho_sharpe"], c["ho_t"], c["post_t"], c["dsr"], "PASS" if c["pass"] else ""))
    L += ["", "Research, not financial advice."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="trader-lab hourly engine")
    sub = ap.add_subparsers(dest="cmd")
    for n in ("fetch", "backtest"):
        p = sub.add_parser(n)
        p.add_argument("--symbols", type=lambda s: s.upper().split(","), default=UNIVERSE)
        p.add_argument("--json", action="store_true")
        p.add_argument("--cost", type=float, default=COST_BPS)
        p.add_argument("--only", type=lambda s: s.split(","))
        p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "hourly-latest.json"))
    a = ap.parse_args(argv)
    try:
        if a.cmd == "fetch":
            for s in a.symbols:
                try:
                    new = parse(fetch(s))
                except LabError as e:
                    print("%-6s skipped: %s" % (s, e))
                    continue
                allb = load(s)
                allb.update(new)
                save(s, allb)
                print("%-6s %5d bars, %4d sessions" % (s, len(allb), len(sessions(allb))))
                time.sleep(0.5)
            return 0
        if a.cmd == "backtest":
            uni = {s: sessions(load(s)) for s in a.symbols if load(s)}
            res = backtest(uni, a.cost, a.only)
            if a.write:
                os.makedirs(RESULTS, exist_ok=True)
                with open(a.write, "w") as fh:
                    json.dump(res, fh, indent=1, sort_keys=True)
            print(json.dumps(res, indent=1, sort_keys=True) if a.json else report(res))
            return 0
        ap.print_help()
        return 1
    except LabError as e:
        print("hourly.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
