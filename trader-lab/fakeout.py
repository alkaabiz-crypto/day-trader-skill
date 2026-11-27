#!/usr/bin/env python3
"""Can we tell a fake breakout before it fails? Pre-registered test of the common fake-out warning signs.

    python3 fakeout.py run [--write]   # uses data/long (Tiingo 5-minute bars, 40 names) -> results/fakeout.json

The owner, after the stocks-in-play book lost on all four trades of 2026-11-25 (a fake-out open: SPY dipped,
then rallied 1.6%): "I want u to know how to signal a fake signal bcz fake signals always happens."

PRE-REGISTERED 2026-11-25, committed before any result. Not to be changed:
  Setups: the live stocks-in-play book exactly (autopaper.SIP): each day, the top 5 of lab.UNIVERSE by first-candle
    relative volume (first 5-minute candle's volume / its average over the prior 14 full sessions), rvol >= 1.5,
    first candle not a doji. Side = the first candle's colour. Entry: a stop order at the first candle's high (long)
    or low (short), live from 9:35 to 15:45; fill at the level, or the open if the candle opens past it. Stop: one
    first-candle height from the entry; the fill candle can stop out (at the stop). Else sold at the 15:45 candle's
    close. Costs 5 bps a round trip. Full sessions only (half days dropped); the prior close is the last full session's.
  A fake = a trade that hits its stop.
  Warning signs, each known no later than the moment of entry (no look-ahead):
    market_against  SPY's first candle points the other way (QQQ's for SPY itself)
    tiny_candle     first candle's height < half its average over the prior 14 sessions (stop sits inside noise)
    big_gap         the open gapped > 2% in the trade's direction (an exhausted move)
    weak_close      the first candle closed in its wrong half (a long whose green candle closed in its lower half:
                    a rejection wick; mirrored for shorts)
    extreme_rvol    relative volume > 5 (a crowded name)
    instant_fill    the level breaks in the very next candle (9:35-9:40)
    late_fill       the level breaks only after 10:30
  And one changed entry, the classic fake-out fix:
    close_confirm   don't use a stop order; enter only after a 5-minute candle CLOSES past the level, at that close,
                    with the stop at the same price as before (level minus one candle height)
  Split: in-sample before 2025-01-01, judged from 2025-01-01.
  Verdict, per warning sign: a REAL WARNING only if, on the judged years, trades with the sign earn less per trade
    than trades without it with Welch t >= 3, the same direction holds in-sample, and the judged years have at least
    30 flagged trades. close_confirm is REAL only if the paired per-setup difference (confirm minus stop order) has
    judged t >= 3 and is positive in-sample. Eight tests at t >= 3 is near a Bonferroni 5% bar.
  Reported: fake rates with and without each sign, and what skipping the flagged trades would have done to the
    judged-years P&L at $2,000 a trade (the live size).
Research, not financial advice.
"""

import argparse
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402

RESULTS = os.path.join(HERE, "results")
TOP, MIN_RVOL, LOOKBACK = 5, 1.5, 14
LAST_SLOT = 75                     # the 15:45 candle: the live book flattens at 15:50 on its close
COST_BPS = 5.0
PER_TRADE = 2000.0
SPLIT, T_BAR, MIN_FLAGGED = "2025-01-01", 3.0, 30
FLAGS = ["market_against", "tiny_candle", "big_gap", "weak_close", "extreme_rvol", "instant_fill", "late_fill"]


def load_all():
    out = {}
    for s in lab.UNIVERSE:
        bars = lab.load_store(s, lab.LONG_STORE)
        if bars:
            out[s] = [(d, b) for d, b in lab.sessions_of(lab.drop_after_early_close(bars)) if len(b) == lab.SESSION_BARS]
    return out


def exit_after(bars, k, side, stop):
    """Walk from candle k (the fill candle) to the close; the stop wins inside a candle."""
    for j in range(k, LAST_SLOT + 1):
        b = bars[j]
        if (side > 0 and b["l"] <= stop) or (side < 0 and b["h"] >= stop):
            px = stop if j == k else (min(b["o"], stop) if side > 0 else max(b["o"], stop))
            return px, "stop"
    return bars[LAST_SLOT]["c"], "close"


def stop_entry(bars, side, level, dist):
    """The live rule: (fill slot, entry, exit, why) or None."""
    for k in range(1, LAST_SLOT + 1):
        b = bars[k]
        if (side > 0 and b["h"] >= level) or (side < 0 and b["l"] <= level):
            px = max(level, b["o"]) if side > 0 else min(level, b["o"])
            x, why = exit_after(bars, k, side, px - side * dist)
            return k, px, x, why
    return None


def confirm_entry(bars, side, level, dist):
    """Enter at the close of the first candle that closes past the level; stop at level - side*dist."""
    stop = level - side * dist
    for k in range(1, LAST_SLOT):
        c = bars[k]["c"]
        if (side > 0 and c > level) or (side < 0 and c < level):
            x, why = exit_after(bars, k + 1, side, stop) if k + 1 <= LAST_SLOT else (c, "close")
            if why == "stop" and k + 1 <= LAST_SLOT:
                b = bars[k + 1]   # the stop on the first candle after entry can gap: use its open if worse
                if (side > 0 and b["l"] <= stop) or (side < 0 and b["h"] >= stop):
                    x = min(b["o"], stop) if side > 0 else max(b["o"], stop)
            return k, c, x, why
    return None


def ret(side, entry, exit_px):
    return side * (exit_px / entry - 1) - COST_BPS / 1e4


def flags_of(s, bars, side, rv, avg_range, prev_close, ref_first, fill_slot):
    b = bars[0]
    rng = b["h"] - b["l"]
    pos = (b["c"] - b["l"]) / rng if rng > 0 else 0.5
    ref_dir = 0 if ref_first is None else (1 if ref_first["c"] > ref_first["o"] else (-1 if ref_first["c"] < ref_first["o"] else 0))
    return {
        "market_against": ref_dir == -side,
        "tiny_candle": rng < 0.5 * avg_range,
        "big_gap": prev_close > 0 and side * (b["o"] - prev_close) / prev_close > 0.02,
        "weak_close": (pos < 0.5) if side > 0 else (pos > 0.5),
        "extreme_rvol": rv > 5,
        "instant_fill": fill_slot == 1,
        "late_fill": fill_slot is not None and fill_slot >= 12,
    }


def build(data):
    idx = {s: {d: i for i, (d, _) in enumerate(ss)} for s, ss in data.items()}
    first = {s: {d: b[0] for d, b in ss} for s, ss in data.items()}
    dates = sorted({d for ss in data.values() for d, _ in ss})
    rows = []
    for d in dates:
        cands = []
        for s, ss in data.items():
            i = idx[s].get(d)
            if i is None or i < LOOKBACK:
                continue
            prior = ss[i - LOOKBACK:i]
            bars = ss[i][1]
            b = bars[0]
            avg_v = sum(p[1][0]["v"] for p in prior) / LOOKBACK
            if avg_v <= 0 or b["c"] == b["o"]:
                continue
            avg_r = sum(p[1][0]["h"] - p[1][0]["l"] for p in prior) / LOOKBACK
            cands.append((b["v"] / avg_v, s, bars, avg_r, ss[i - 1][1][-1]["c"]))
        cands.sort(key=lambda r: -r[0])
        for rv, s, bars, avg_r, pc in cands[:TOP]:
            if rv < MIN_RVOL:
                continue
            b = bars[0]
            side = 1 if b["c"] > b["o"] else -1
            level, dist = (b["h"] if side > 0 else b["l"]), b["h"] - b["l"]
            base = stop_entry(bars, side, level, dist)
            conf = confirm_entry(bars, side, level, dist)
            ref = first.get("QQQ" if s == "SPY" else "SPY", {}).get(d)
            row = {"date": d, "symbol": s, "side": side, "rvol": rv,
                   "base": None if base is None else {"slot": base[0], "ret": ret(side, base[1], base[2]), "why": base[3]},
                   "confirm": None if conf is None else {"slot": conf[0], "ret": ret(side, conf[1], conf[2]), "why": conf[3]}}
            row["flags"] = flags_of(s, bars, side, rv, avg_r, pc, ref, None if base is None else base[0])
            rows.append(row)
    return rows


def tstat(x):
    if len(x) < 2:
        return 0.0
    sd = statistics.stdev(x)
    return statistics.mean(x) / (sd / math.sqrt(len(x))) if sd > 0 else 0.0


def welch(a, b):
    """t of mean(a) - mean(b)."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    se = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    return (statistics.mean(a) - statistics.mean(b)) / se if se > 0 else 0.0


def flag_stats(trades, flag):
    on = [t for t in trades if t["flags"][flag]]
    off = [t for t in trades if not t["flags"][flag]]
    r_on, r_off = [t["base"]["ret"] for t in on], [t["base"]["ret"] for t in off]
    fake = lambda ts: sum(t["base"]["why"] == "stop" for t in ts) / len(ts) if ts else None  # noqa: E731
    return {"n_flagged": len(on), "n_clean": len(off),
            "fake_rate_flagged": fake(on), "fake_rate_clean": fake(off),
            "bps_flagged": 1e4 * statistics.mean(r_on) if r_on else None,
            "bps_clean": 1e4 * statistics.mean(r_off) if r_off else None,
            "t_clean_minus_flagged": welch(r_off, r_on),
            "usd_all": PER_TRADE * sum(r_on + r_off), "usd_skip_flagged": PER_TRADE * sum(r_off)}


def cmd_run(a):
    rows = build(load_all())
    traded = [r for r in rows if r["base"]]
    is_t = [r for r in traded if r["date"] < SPLIT]
    jd_t = [r for r in traded if r["date"] >= SPLIT]
    res = {"setups": len(rows), "trades": len(traded), "base": {}, "flags": {}, "close_confirm": {}}
    for name, ts in (("in_sample", is_t), ("judged", jd_t)):
        r = [t["base"]["ret"] for t in ts]
        res["base"][name] = {"trades": len(r), "bps": 1e4 * statistics.mean(r) if r else 0.0, "t": tstat(r),
                             "fake_rate": sum(t["base"]["why"] == "stop" for t in ts) / len(ts) if ts else None,
                             "usd": PER_TRADE * sum(r)}
    print("stocks-in-play, stop-order entry: IS %d trades %+.1f bp (t %+.2f, %.0f%% faked) | judged %d trades %+.1f bp "
          "(t %+.2f, %.0f%% faked, $%+.0f at $2,000 a trade)" % (
              res["base"]["in_sample"]["trades"], res["base"]["in_sample"]["bps"], res["base"]["in_sample"]["t"],
              100 * (res["base"]["in_sample"]["fake_rate"] or 0), res["base"]["judged"]["trades"],
              res["base"]["judged"]["bps"], res["base"]["judged"]["t"], 100 * (res["base"]["judged"]["fake_rate"] or 0),
              res["base"]["judged"]["usd"]))
    print("%-15s | %-38s | %-38s | verdict" % ("warning sign", "in-sample: fake% flag/clean, bp, t", "judged: fake% flag/clean, bp, t"))
    for f in FLAGS:
        si, sj = flag_stats(is_t, f), flag_stats(jd_t, f)
        real = (sj["t_clean_minus_flagged"] >= T_BAR and si["t_clean_minus_flagged"] > 0 and sj["n_flagged"] >= MIN_FLAGGED)
        res["flags"][f] = {"in_sample": si, "judged": sj, "verdict": "REAL WARNING" if real else "NOT PROVEN"}
        fmt = lambda s: "%4d %3.0f%%/%3.0f%% %+6.1f/%+6.1f t%+5.2f" % (  # noqa: E731
            s["n_flagged"], 100 * (s["fake_rate_flagged"] or 0), 100 * (s["fake_rate_clean"] or 0),
            s["bps_flagged"] or 0, s["bps_clean"] or 0, s["t_clean_minus_flagged"])
        print("%-15s | %-38s | %-38s | %s" % (f, fmt(si), fmt(sj), res["flags"][f]["verdict"]))
    for name, ts in (("in_sample", [r for r in rows if r["date"] < SPLIT]), ("judged", [r for r in rows if r["date"] >= SPLIT])):
        diff = [(r["confirm"]["ret"] if r["confirm"] else 0.0) - (r["base"]["ret"] if r["base"] else 0.0) for r in ts]
        cr = [r["confirm"]["ret"] for r in ts if r["confirm"]]
        res["close_confirm"][name] = {"setups": len(ts), "trades": len(cr), "bps": 1e4 * statistics.mean(cr) if cr else 0.0,
                                      "fake_rate": sum(r["confirm"]["why"] == "stop" for r in ts if r["confirm"]) / len(cr) if cr else None,
                                      "paired_bps": 1e4 * statistics.mean(diff) if diff else 0.0, "paired_t": tstat(diff),
                                      "usd": PER_TRADE * sum(cr)}
    ci, cj = res["close_confirm"]["in_sample"], res["close_confirm"]["judged"]
    res["close_confirm"]["verdict"] = "REAL FIX" if (cj["paired_t"] >= T_BAR and ci["paired_bps"] > 0) else "NOT PROVEN"
    print("close_confirm   | IS %d trades %+.1f bp, %.0f%% faked, vs stop order %+.1f bp/setup t %+.2f | judged %d trades "
          "%+.1f bp, %.0f%% faked, vs stop order %+.1f bp/setup t %+.2f, $%+.0f | %s" % (
              ci["trades"], ci["bps"], 100 * (ci["fake_rate"] or 0), ci["paired_bps"], ci["paired_t"], cj["trades"],
              cj["bps"], 100 * (cj["fake_rate"] or 0), cj["paired_bps"], cj["paired_t"], cj["usd"],
              res["close_confirm"]["verdict"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "fakeout.json"))
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
