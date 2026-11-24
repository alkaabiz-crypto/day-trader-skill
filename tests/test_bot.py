import unittest

from _load import load

bot = load("trader-lab", "bot")


class Fx(unittest.TestCase):
    def test_direction(self):
        self.assertEqual(bot.direction(["breakout_20d", "overbought"]), "buy")
        self.assertEqual(bot.direction(["reclaim_ma20"]), "buy")
        self.assertEqual(bot.direction(["breakdown_20h", "oversold"]), "sell")
        self.assertIsNone(bot.direction(["oversold", "oversold_bounce"]))      # RSI setups are not traded
        self.assertIsNone(bot.direction(["reclaim_ma20", "breakdown_20h"]))    # both ways: skip

    def test_new_setups(self):
        rows = [{"symbol": "A", "setups": ["breakout_20d"]}, {"symbol": "B", "setups": ["breakdown_20h", "oversold"]},
                {"symbol": "C", "setups": []}]
        got = bot.new_setups(rows, {"A": ["breakout_20d"], "B": ["breakdown_20h"]})
        self.assertEqual(got, {"B": ["oversold"]})

    def test_plan_sizes_to_ten_dollars(self):
        p = bot.fx_plan("EURUSD=X", "sell", 1.10, 0.002)
        self.assertAlmostEqual(p["stop"], 1.103)
        self.assertAlmostEqual(p["target"], 1.094)
        self.assertAlmostEqual(p["notional_usd"] * 0.003 / 1.10, 10.0, places=1)
        self.assertEqual(p["cost_bps"], 2.0)
        self.assertEqual(bot.fx_plan("BTC-USD", "buy", 60000, 300)["cost_bps"], 6.0)
        self.assertEqual(bot.fx_plan("LTC-USD", "buy", 40, 0.3)["cost_bps"], 15.0)
        self.assertEqual(bot.fx_plan("GBPJPY=X", "buy", 208, 0.3)["cost_bps"], 3.0)

    def test_groups_nights_and_variants(self):
        self.assertEqual([bot.group(s) for s in ("BTC-USD", "SI=F", "EURUSD=X")], ["crypto", "metal", "forex"])
        self.assertEqual(bot.nights(86400 * 10 + 3600 * 22, 86400 * 11 + 3600 * 2), 1)
        self.assertEqual(bot.nights(86400 * 10 + 3600, 86400 * 10 + 3600 * 20), 0)
        import datetime as dt
        sat = dt.datetime(2026, 11, 28, 12)
        self.assertFalse(bot.fx_variant_ok("noweekend", "EURUSD=X", "buy", sat, None))
        self.assertTrue(bot.fx_variant_ok("btctrend", "EURUSD=X", "buy", sat, -1))     # FX unaffected
        self.assertFalse(bot.fx_variant_ok("btctrend", "ETH-USD", "buy", sat, -1))
        self.assertTrue(bot.fx_variant_ok("btctrend", "ETH-USD", "sell", sat, -1))
        self.assertTrue(bot.stock_variant_ok("fresh", {"bar_start": "11:05"}, "11:17", None))
        self.assertFalse(bot.stock_variant_ok("fresh", {"bar_start": "09:45"}, "11:17", None))
        self.assertTrue(bot.stock_variant_ok("first", {}, "10:17", None))
        self.assertFalse(bot.stock_variant_ok("first", {}, "11:17", None))
        self.assertFalse(bot.stock_variant_ok("spytrend", {}, "11:17", False))

    def test_atr(self):
        bars = [(i, 10, 11, 9, 10) for i in range(20)]
        self.assertAlmostEqual(bot.atr(bars, 14), 2.0)

    def test_fill_stop_first_and_short_sign(self):
        H = 3600
        bars = [(0, 100, 101, 99, 100), (H, 100, 100.5, 99.5, 100), (2 * H, 100, 103, 97, 100)]
        e, x, how, t0, t1 = bot.fill_hourly(bars, H, "buy", 98, 102, 24, 10 * H)
        self.assertEqual((e, x, how, t0, t1), (100, 98, "stop", H, 3 * H))
        e, x, how, _, _ = bot.fill_hourly(bars, H, "sell", 102, 98, 24, 10 * H)
        self.assertEqual((x, how), (102, "stop"))
        self.assertLess(bot.pnl_usd("sell", 100, 102, 1000, 0), 0)
        self.assertAlmostEqual(bot.pnl_usd("sell", 100, 98, 1000, 2), 20 - 0.2)

    def test_time_exit_and_still_open(self):
        H = 3600
        bars = [(i * H, 100, 100.5, 99.5, 100 + i * 0.01) for i in range(30)]
        self.assertIsNone(bot.fill_hourly(bars[:10], 0, "buy", 90, 110, 24, 10 * H))
        e, x, how, _, _ = bot.fill_hourly(bars, 0, "buy", 90, 110, 24, 30 * H)
        self.assertEqual(how, "time")
        self.assertAlmostEqual(x, 100.23)


class Stocks(unittest.TestCase):
    def test_caps(self):
        t = lambda d, r=10.0: {"track": "stocks", "date": d, "risk_usd": r}
        self.assertEqual(bot.stock_caps([], "2026-11-24"), 2)
        self.assertEqual(bot.stock_caps([t("2026-11-24")] * 4, "2026-11-24"), 1)
        self.assertEqual(bot.stock_caps([t("2026-11-24")] * 5, "2026-11-24"), 0)
        self.assertEqual(bot.stock_caps([t("2026-11-24", 20.0)] * 2, "2026-11-24"), 1)   # $40 of $50 risk used
        self.assertEqual(bot.stock_caps([t("2026-11-23")] * 5, "2026-11-24"), 2)

    def test_failed_breakout_is_skipped(self):
        self.assertTrue(bot.still_above({"or_high": 100.0}, 100.5))
        self.assertFalse(bot.still_above({"or_high": 100.0}, 99.9))
        self.assertFalse(bot.still_above({"or_high": 100.0}, 0))

    def test_next_slot_has_no_look_ahead(self):
        self.assertEqual(bot.next_slot("10:17"), 10)    # 10:20 bar, not the 10:15 one already under way
        self.assertEqual(bot.next_slot("10:20"), 10)
        self.assertEqual(bot.slot_time(10), "10:20")


if __name__ == "__main__":
    unittest.main()
