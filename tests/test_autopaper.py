import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import autopaper as ap  # noqa: E402


def state(cash=10000.0, positions=None):
    return {"cash": cash, "positions": positions or [], "buys": {}, "realized": {}, "start": None}


def pos(sym="AAA", qty=10, entry=100.0, stop=99.0, target=102.0, day="2026-11-24", bar_end="10:50"):
    return {"symbol": sym, "qty": qty, "entry": entry, "stop": stop, "target": target, "date": day,
            "entry_time": day + " " + bar_end, "entry_bar_end": bar_end}


def bar(t, o, h, l, c):
    return {"t": t, "o": o, "h": h, "l": l, "c": c}


NOW = datetime.datetime(2026, 11, 24, 11, 52)


class Autopaper(unittest.TestCase):
    def test_paper_only_no_order_code(self):
        src = open(ap.__file__).read()
        for word in ("place_stock_order", "paper-api", "api.alpaca.markets/v2/orders"):
            self.assertNotIn(word, src)

    def test_new_york_clock(self):
        f = lambda s: ap.utc_to_ny(datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")).strftime("%H:%M")  # noqa: E731
        self.assertEqual(f("2026-11-24 15:52"), "10:52")   # winter, UTC-5
        self.assertEqual(f("2026-07-01 14:52"), "10:52")   # summer, UTC-4
        self.assertEqual(f("2026-03-08 07:00"), "03:00")   # the spring switch

    def test_stop_wins_when_bar_hits_both(self):
        s = state(cash=9000.0, positions=[pos()])
        closed, _ = ap.manage(s, lambda _: [bar("10:50", 100, 103, 98, 101)], NOW)
        self.assertEqual(closed[0]["why"], "stop")
        self.assertAlmostEqual(closed[0]["exit"], 99.0)

    def test_bars_before_entry_ignored_and_target(self):
        s = state(cash=9000.0, positions=[pos()])
        closed, _ = ap.manage(s, lambda _: [bar("10:45", 100, 100, 90, 95), bar("10:55", 101, 102.5, 100.5, 102)], NOW)
        self.assertEqual(closed[0]["why"], "target")
        self.assertAlmostEqual(closed[0]["exit"], 102.0)

    def test_flatten_at_end_of_day(self):
        s = state(cash=9000.0, positions=[pos()])
        late = datetime.datetime(2026, 11, 24, 15, 52)
        closed, _ = ap.manage(s, lambda _: [bar("15:45", 100, 100.5, 99.5, 100.4)], late)
        self.assertEqual(closed[0]["why"], "end of day")
        self.assertEqual(s["positions"], [])

    def test_ledger_consistent(self):
        s = state(cash=10000.0 - 1000.0, positions=[pos()])
        closed, _ = ap.manage(s, lambda _: [bar("10:55", 101, 102.5, 100.5, 102)], NOW)
        cost = (100 + 102) * 10 * 5 / 2 / 1e4
        self.assertAlmostEqual(s["cash"], 10000 + 20 - cost)
        self.assertAlmostEqual(closed[0]["pnl_usd"], round(20 - cost, 2))

    def test_buy_gates(self):
        s = state()
        self.assertFalse(ap.may_buy(s, {}, datetime.datetime(2026, 11, 24, 15, 1))[0])
        s["realized"]["2026-11-24"] = -150.0
        self.assertFalse(ap.may_buy(s, {}, NOW)[0])
        s = state(positions=[pos("A"), pos("B"), pos("C")])
        self.assertFalse(ap.may_buy(s, {}, NOW)[0])
        s = state()
        s["buys"]["2026-11-24"] = 4
        self.assertFalse(ap.may_buy(s, {}, NOW)[0])
        self.assertTrue(ap.may_buy(state(), {}, NOW)[0])

    def test_chain_buys_on_pass_only(self):
        def skill(args):
            name = args[0]
            if "scan.py" in name:
                return {"hits": [{"symbol": "AAA", "bar_start": "11:30"}, {"symbol": "BBB", "bar_start": "11:35"}]}, None
            if "entry.py" in name:
                return {"status": "triggered", "minutes_since": 30, "last": {"close": 100.0, "vs_level_pct": 0.2}}, None
            if "exit.py" in name:
                return {"stop": 99.0, "target": 102.0}, None
            if "size.py" in name:
                return {"sizing": {"qty": 20}}, None
            sym = os.path.basename(args[args.index("--orders") + 1])
            return {"results": [{"verdict": "PASS" if "AAA" in sym else "BLOCK", "reasons": ["test"]}]}, None
        s = state()
        new, log = ap.find_buys(s, {}, NOW, ["AAA", "BBB"], True, skill=skill)
        self.assertEqual([p["symbol"] for p in new], ["AAA"])
        self.assertAlmostEqual(s["cash"], 10000 - 20 * 100.02)
        self.assertTrue(any("BBB: risk BLOCK" in x for x in log))


class HalfDay(unittest.TestCase):
    def test_half_day_sells_at_the_last_candle(self):
        # the day after Thanksgiving closes at 13:00: the 15:52 run sells at the 12:55 candle's close
        s = state(cash=9000.0, positions=[pos(day="2026-11-27", bar_end="10:50")])
        bars = [bar("10:55", 100, 100.5, 99.5, 100.2), bar("12:55", 100.2, 100.6, 100.0, 100.4)]
        closed, _ = ap.manage(s, lambda _: bars, datetime.datetime(2026, 11, 27, 15, 52))
        self.assertEqual(closed[0]["why"], "end of day")
        self.assertAlmostEqual(closed[0]["exit"], 100.4)
        self.assertEqual(closed[0]["exit_time"], "2026-11-27 12:55")

    def test_no_buys_after_the_half_day_close_without_fresh_breakouts(self):
        now = datetime.datetime(2026, 11, 27, 13, 37)
        self.assertFalse(ap.fresh("12:50", now, 30))     # the last candle closed 12:55, 42 minutes before


class Books(unittest.TestCase):
    def test_fresh_window(self):
        now = datetime.datetime(2026, 11, 25, 10, 22)
        self.assertTrue(ap.fresh("10:00", now, 30))      # closed 10:05, 17 minutes ago
        self.assertFalse(ap.fresh("09:45", now, 30))     # closed 9:50, 32 minutes ago
        self.assertFalse(ap.fresh(None, now, 30))

    def test_sip_pick_ranks_by_relative_volume(self):
        days = {}
        for k, (s, v_today, green) in enumerate([("A", 3000, True), ("B", 2000, False), ("C", 1100, True)]):
            d = {"2026-11-%02d" % (i + 1): [{"t": "09:30", "o": 10, "h": 11, "l": 9, "c": 10.5, "v": 1000}]
                 for i in range(14)}
            o, c = (10, 10.5) if green else (10.5, 10)
            d["2026-11-25"] = [{"t": "09:30", "o": o, "h": 11, "l": 9.8, "c": c, "v": v_today}]
            days[s] = d
        picks = ap.sip_pick(days, "2026-11-25")
        self.assertEqual([p[0] for p in picks], ["A", "B"])          # C's ratio 1.1 is under 1.5
        self.assertEqual(picks[0][1:3], (1, 11))                     # green: buy stop at the high
        self.assertEqual(picks[1][1:3], (-1, 9.8))                   # red: short at the low

    def test_sip_order_fills_after_placement_and_stops(self):
        st = {"cash": 10000.0, "positions": [], "realized": {}, "start": None, "done": [],
              "orders": [{"symbol": "A", "side": 1, "level": 11.0, "dist": 2.0, "date": "2026-11-25",
                          "active_from": "09:35"}]}
        bars = [{"t": "09:30", "o": 10, "h": 12, "l": 9, "c": 11},          # before placement: ignored
                {"t": "09:35", "o": 10.8, "h": 11.2, "l": 10.7, "c": 11.1},  # fills at 11.00
                {"t": "09:40", "o": 11, "h": 11.1, "l": 8.9, "c": 9}]        # stop at 9.00
        closed, log, _ = ap.sip_step(st, lambda s: bars, datetime.datetime(2026, 11, 25, 10, 7))
        self.assertEqual(closed[0]["why"], "stop")
        self.assertAlmostEqual(closed[0]["entry"], 11.0)
        self.assertAlmostEqual(closed[0]["exit"], 9.0)
        self.assertLess(abs(st["cash"] - (10000 + closed[0]["pnl_usd"])), 0.01)

    def test_short_close_accounting(self):
        st = {"cash": 10000.0 - 100 * 10.0, "realized": {}}
        pos = {"symbol": "B", "qty": 100, "entry": 10.0, "side": -1, "date": "2026-11-25", "entry_time": "x"}
        t = ap.book_close(st, pos, 9.0, "2026-11-25 15:50", "end of day", 0.0)
        self.assertAlmostEqual(t["pnl_usd"], 100.0)
        self.assertAlmostEqual(st["cash"], 10100.0)

    def test_fed_buys_day_before_and_sells_at_open(self):
        import tempfile
        old = ap.BOOK
        ap.BOOK = tempfile.mkdtemp()
        try:
            bars = [{"t": "15:45", "o": 600, "h": 601, "l": 599, "c": 600.0}]
            st, closed, log = ap.run_fed(datetime.datetime(2026, 12, 8, 15, 52), lambda s: bars, ["2026-12-09"])
            self.assertEqual(st["positions"][0]["qty"], 16)
            ap.save_json(os.path.join(ap.BOOK, "fed_state.json"), st)
            open_bars = [{"t": "09:30", "o": 603.0, "h": 604, "l": 602, "c": 603.5}]
            st, closed, log = ap.run_fed(datetime.datetime(2026, 12, 9, 9, 37), lambda s: open_bars, ["2026-12-09"])
            self.assertEqual(closed[0]["exit"], 603.0)
            self.assertFalse(st["positions"])
            self.assertGreater(closed[0]["pnl_usd"], 0)
        finally:
            ap.BOOK = old


if __name__ == "__main__":
    unittest.main()
