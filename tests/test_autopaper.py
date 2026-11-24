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
                return {"hits": [{"symbol": "AAA"}, {"symbol": "BBB"}]}, None
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


if __name__ == "__main__":
    unittest.main()
