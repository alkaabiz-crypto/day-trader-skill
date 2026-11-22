import os
import tempfile
import unittest

from _load import load

lab = load("trader-lab", "lab")
N = lab.SESSION_BARS


def bar(o, h, l, c, v=1000):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


def flat_day(px=100.0, n=N):
    return [dict(bar(px, px, px, px), slot=i) for i in range(n)]


def run(fn, bars, p, ctx=None, full=True):
    return lab.run_day(fn, bars, ctx or {"prev_close": None}, p, full)


class Book(unittest.TestCase):
    def test_fill_at_next_open_and_flat_at_close(self):
        d = flat_day()
        d[0] = dict(bar(100, 101, 99.5, 100.8), slot=0)   # green first bar
        d[1] = dict(bar(100.9, 101, 100.9, 101), slot=1)
        for i in range(2, N):
            d[i] = dict(bar(101, 102, 101, 102), slot=i)
        trades, live = run(lab.s_orb5, d, {"stop": "none"})
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual((t["side"], t["entry"], t["entry_slot"]), (1, 100.9, 1))
        self.assertEqual((t["exit"], t["exit_slot"]), (102, N - 1))
        self.assertIsNone(live)

    def test_stop_fills_at_stop_or_gap_open(self):
        d = flat_day(100.0)
        d[0] = dict(bar(100, 100.5, 99.0, 100.4), slot=0)  # stop = 99.0
        d[1] = dict(bar(100.4, 100.5, 99.5, 99.8), slot=1)
        d[2] = dict(bar(99.6, 99.7, 98.5, 98.6), slot=2)   # trades through 99.0
        trades, _ = run(lab.s_orb5, d, {"stop": "bar"})
        self.assertEqual(trades[0]["exit"], 99.0)
        self.assertEqual(trades[0]["exit_slot"], 2)
        d[2] = dict(bar(98.0, 98.2, 97.5, 98.0), slot=2)   # gaps below the stop
        trades, _ = run(lab.s_orb5, d, {"stop": "bar"})
        self.assertEqual(trades[0]["exit"], 98.0)

    def test_short_side_and_live_position(self):
        d = flat_day(100.0)
        d[0] = dict(bar(100, 100.2, 99, 99.2), slot=0)     # red first bar -> short
        trades, live = run(lab.s_orb5, d[:5], {"stop": "bar"}, full=False)
        self.assertEqual(trades, [])
        self.assertEqual(live["side"], -1)
        self.assertEqual(live["stop"], 100.2)

    def test_trade_bps_includes_cost(self):
        t = {"side": -1, "entry": 100.0, "exit": 99.0}
        self.assertAlmostEqual(lab.trade_bps(t, 3.0), 97.0)


class StopEntry(unittest.TestCase):
    def test_same_bar_entry_and_stop_fills_at_the_stop(self):
        d = flat_day(100.0)
        d[0] = dict(bar(100, 100.2, 99.0, 99.2), slot=0)    # red bar: sell stop at 99.0
        d[1] = dict(bar(99.5, 99.9, 98.8, 99.4), slot=1)    # trades down through 99.0, then up past the stop
        ctx = {"prev_close": None, "rvol": 2.0, "rvol_rank": 1, "atr14": 2.0}
        trades, _ = run(lab.s_sip, d, {"top": 5, "min_rvol": 1.0, "stop": "atr10"}, ctx)
        t = trades[0]
        self.assertEqual((t["side"], t["entry"], t["entry_slot"]), (-1, 99.0, 1))
        self.assertAlmostEqual(t["exit"], 99.2)              # the stop, not the 99.5 open before the entry

    def test_sip_needs_rank_and_rvol(self):
        d = flat_day(100.0)
        d[0] = dict(bar(100, 101, 99.9, 100.9), slot=0)
        d[1] = dict(bar(100.9, 101.5, 100.9, 101.4), slot=1)
        p = {"top": 5, "min_rvol": 1.5, "stop": "bar"}
        for rv, rank, n in ((2.0, 1, 1), (1.2, 1, 0), (2.0, 6, 0)):
            ctx = {"prev_close": None, "rvol": rv, "rvol_rank": rank, "atr14": 2.0}
            trades, _ = run(lab.s_sip, d, p, ctx)
            self.assertEqual(len(trades), n, (rv, rank))
        ctx = {"prev_close": None, "rvol": 2.0, "rvol_rank": 1, "atr14": 2.0}
        trades, _ = run(lab.s_sip, d, p, ctx)
        self.assertEqual(trades[0]["entry"], 101)            # the break of the first bar's high

    def test_rvol_and_atr(self):
        ss = []
        for k in range(15):
            day = flat_day(100.0)
            day[0] = dict(bar(100, 101, 99, 100, 300 if k == 14 else 100), slot=0)
            ss.append(("d%02d" % k, day))
        self.assertAlmostEqual(lab.first_bar_rvol(ss, 14), 3.0)
        self.assertIsNone(lab.first_bar_rvol(ss, 5))
        self.assertAlmostEqual(lab.atr14(ss, 14), 2.0)
        quiet = flat_day()
        quiet[0] = dict(bar(100, 101, 99, 100, 150), slot=0)  # B: rvol 1.5 < A's 3.0
        xs = lab.cross_section({"A": ss, "B": ss[:14] + [("d14", quiet)]})
        self.assertEqual(xs[("B", "d14")]["rvol_rank"], 2)
        self.assertEqual(xs[("A", "d14")]["rvol_rank"], 1)


class Strategies(unittest.TestCase):
    def test_orb_breakout_once_with_mid_stop(self):
        d = flat_day(100.0)
        d[0] = dict(bar(100, 101, 99, 100), slot=0)
        d[1] = dict(bar(100, 100.5, 99.5, 100), slot=1)
        d[2] = dict(bar(100, 100.5, 99.5, 100), slot=2)
        d[3] = dict(bar(100, 101.5, 100, 101.4), slot=3)   # closes above 101
        for i in range(4, N):
            d[i] = dict(bar(101.4, 101.6, 101.2, 101.5), slot=i)
        trades, _ = run(lab.s_orb, d, {"bars": 3, "stop": "mid", "last": 23}, {"prev_close": None})
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["side"], 1)
        self.assertEqual(trades[0]["entry_slot"], 4)

    def test_imom_follows_the_morning(self):
        d = flat_day(100.0)
        for i in range(N):
            d[i] = dict(bar(101, 101, 101, 101), slot=i)    # up 1% from 100 by 10:00
        trades, _ = run(lab.s_imom, d, {"entry": 72, "min_bps": 25}, {"prev_close": 100.0})
        self.assertEqual(trades[0]["side"], 1)
        self.assertEqual(trades[0]["entry_slot"], 72)
        trades, _ = run(lab.s_imom, d, {"entry": 72, "min_bps": 200}, {"prev_close": 100.0})
        self.assertEqual(trades, [])

    def test_gap_fade_and_go(self):
        d = flat_day(102.0)
        fade, _ = run(lab.s_gap, d, {"min_pct": 1.0, "mode": "fade"}, {"prev_close": 100.0})
        go, _ = run(lab.s_gap, d, {"min_pct": 1.0, "mode": "go"}, {"prev_close": 100.0})
        self.assertEqual(fade[0]["side"], -1)
        self.assertEqual(go[0]["side"], 1)

    def test_noise_band_breakout_and_vwap(self):
        d = flat_day(100.0)
        for i in range(5, N):
            d[i] = dict(bar(102, 102, 102, 102), slot=i)     # far above the band at 10:00
        ctx = {"prev_close": 100.0, "sigma_14": [0.005] * N}
        trades, _ = run(lab.s_noise, d, {"lookback": 14, "mult": 1.0}, ctx)
        self.assertEqual(trades[0]["side"], 1)
        self.assertEqual(trades[0]["entry_slot"], 6)
        vw = lab.vwap_series([bar(1, 2, 0, 1, 1), bar(3, 3, 3, 3, 3)])
        self.assertAlmostEqual(vw[-1], (1 * 1 + 3 * 3) / 4.0)

    def test_sigma_table_needs_full_lookback(self):
        ss = [("d%d" % k, flat_day(100.0)) for k in range(5)]
        self.assertIsNone(lab.sigma_table(ss, 4, 10))
        self.assertEqual(lab.sigma_table(ss, 4, 3), [0.0] * N)


class Alpaca(unittest.TestCase):
    def test_parse_keeps_regular_session_5min_bars(self):
        bars = [{"t": "2016-01-04T14:30:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 100},   # 9:30 ET
                {"t": "2016-01-04T13:55:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1},         # pre-market
                {"t": "2016-01-04T21:00:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1},         # 16:00, after
                {"t": "2016-07-05T13:30:00Z", "o": 3, "h": 3, "l": 3, "c": 3, "v": 3}]         # 9:30 EDT
        out = lab.parse_alpaca(bars)
        self.assertEqual(sorted(out), sorted([str(lab.iso_to_epoch("2016-01-04T14:30:00Z")),
                                              str(lab.iso_to_epoch("2016-07-05T13:30:00Z"))]))
        self.assertEqual(out[str(lab.iso_to_epoch("2016-01-04T14:30:00Z"))], [1.0, 2.0, 0.5, 1.5, 100.0])


class AlphaVantage(unittest.TestCase):
    def test_end_labels_are_shifted_to_bar_starts(self):
        csv = ("timestamp,open,high,low,close,volume\n"
               "2016-01-04 16:00:00,5,5,5,5,50\n"
               "2016-01-04 09:40:00,2,2,2,2,20\n"
               "2016-01-04 09:35:00,1,1,1,1,10\n")
        out = lab.parse_av_csv(csv)
        first = str(lab.iso_to_epoch("2016-01-04T14:30:00Z"))      # 9:30 EST bar start
        last = str(lab.iso_to_epoch("2016-01-04T20:55:00Z"))       # 15:55 bar start
        self.assertEqual(out[first][0], 1.0)
        self.assertEqual(out[last][0], 5.0)
        self.assertEqual(len(out), 3)

    def test_start_labels_kept_and_dst(self):
        csv = "timestamp,open,high,low,close,volume\n2016-07-05 09:30:00,1,1,1,1,1\n2016-07-05 09:35:00,2,2,2,2,2\n"
        out = lab.parse_av_csv(csv)
        self.assertIn(str(lab.iso_to_epoch("2016-07-05T13:30:00Z")), out)  # 9:30 EDT

    def test_errors_and_months(self):
        with self.assertRaises(lab.LabError):
            lab.parse_av_csv('{"Information": "rate limit is 25 requests per day"}')
        self.assertEqual(lab.months_back("2016-02", "2015-11"), ["2016-02", "2016-01", "2015-12", "2015-11"])


class StoreAndSplit(unittest.TestCase):
    def test_merge_never_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            lab.save_store("ZZ", {"1": [1, 1, 1, 1, 0], "2": [2, 2, 2, 2, 0]}, tmp)
            allb = lab.merge(lab.load_store("ZZ", tmp), {"2": [9, 9, 9, 9, 0], "3": [3, 3, 3, 3, 0]})
            lab.save_store("ZZ", allb, tmp)
            got = lab.load_store("ZZ", tmp)
            self.assertEqual(sorted(got, key=int), ["1", "2", "3"])
            self.assertEqual(got["2"][0], 9)
            self.assertTrue(os.path.exists(os.path.join(tmp, "ZZ.json.gz")))

    def test_choice_uses_in_sample_only(self):
        mk = lambda name, is_s, oos_s, oos_m: {
            "strategy": name, "params": {"x": is_s},
            "is": {"sharpe": is_s, "trades": 100}, "oos": {"sharpe": oos_s, "mean": oos_m, "t": 1, "trades": 50}}
        chosen = lab.choose([mk("a", 1.0, -9, -1), mk("a", 0.2, 9, 5), mk("b", 2.0, 1, 2)])
        by = {c["strategy"]: c for c in chosen}
        self.assertEqual(by["a"]["params"], {"x": 1.0})   # the OOS winner was NOT picked
        self.assertFalse(by["a"]["keep"])                 # and the IS winner failed OOS
        self.assertTrue(by["b"]["keep"])
        self.assertAlmostEqual(by["b"]["weight"], 1.0)

    def test_labels(self):
        self.assertEqual(lab.label(0.1), "no edge")
        self.assertEqual(lab.label(0.5), "lean long")
        self.assertEqual(lab.label(-0.9), "lean short")                # one weak strategy is never strong
        self.assertEqual(lab.label(-0.9, [1.2]), "lean short")
        self.assertEqual(lab.label(-0.9, [2.6, 3.1]), "strong short")


if __name__ == "__main__":
    unittest.main()
