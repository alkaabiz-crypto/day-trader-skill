import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import calendar2 as c2  # noqa: E402
import insiders as ins  # noqa: E402
import paper500 as p5  # noqa: E402


def weekdays(start, n):
    import datetime
    d, out = datetime.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


class Calendar(unittest.TestCase):
    def test_fomc_cycle_days(self):
        dates = weekdays("2020-01-01", 40)
        cyc = c2.fomc_days(dates, [dates[5], dates[30]])
        self.assertEqual(cyc[dates[4]], -1)      # the day before
        self.assertEqual(cyc[dates[5]], 0)
        self.assertEqual(cyc[dates[14]], 9)      # week 2 starts
        self.assertEqual(cyc[dates[29]], -1)     # the day before the next meeting
        self.assertIn(9, c2.EVEN)
        self.assertNotIn(5, c2.EVEN)

    def test_holidays_and_unscheduled(self):
        dates = [d for d in weekdays("2012-10-22", 10) if d not in ("2012-10-29", "2012-10-30")]
        self.assertEqual(c2.holidays(dates), [])              # Sandy closures aren't holidays
        dates = [d for d in weekdays("2020-07-01", 5) if d != "2020-07-03"]
        self.assertEqual(c2.holidays(dates), ["2020-07-03"])
        self.assertEqual(c2.pre_holiday_days(dates), {"2020-07-02"})

    def test_opex_week(self):
        dates = weekdays("2024-03-01", 25)
        w = c2.opex_weeks(dates)
        self.assertIn("2024-03-15", w)                         # third Friday of March 2024
        self.assertEqual(w["2024-03-15"][0], "2024-03-11")


class Insiders(unittest.TestCase):
    def test_sec_date(self):
        self.assertEqual(ins.sec_date("31-MAR-2023"), "2023-03-31")
        self.assertEqual(ins.sec_date("2023-03-31"), "2023-03-31")

    def test_cluster_rule(self):
        rows = [["2020-01-02", "1", "ABC", "o1", 40000], ["2020-01-10", "1", "ABC", "o2", 40000],
                ["2020-01-20", "1", "ABC", "o3", 30000],                              # 3 owners, $110k -> event
                ["2020-02-01", "1", "ABC", "o4", 90000],                              # inside the 90-day quiet time
                ["2020-01-02", "2", "XYZ", "a", 90000], ["2020-01-03", "2", "XYZ", "a", 90000],
                ["2020-01-04", "2", "XYZ", "b", 90000]]                               # only 2 owners
        self.assertEqual(ins.events(rows), [("2020-01-20", "1", "ABC")])

    def test_cluster_needs_value(self):
        rows = [["2020-01-02", "1", "ABC", o, 10000] for o in ("a", "b", "c")]
        self.assertEqual(ins.events(rows), [])


class Account(unittest.TestCase):
    def test_cash_earns_bill_and_position_pays_cost(self):
        days = ["2020-01-02", "2020-01-03", "2020-01-06"]
        rf = {d: 0.0001 for d in days}
        pos = [{"entry": "2020-01-02", "exit": "2020-01-06", "cost": 0.002,
                "rets": {"2020-01-03": 0.01, "2020-01-06": 0.0}}]
        path = p5.account(days, pos, rf)
        self.assertAlmostEqual(path[0][1], 500 * 1.0001)                    # nothing open: T-bill
        self.assertAlmostEqual(path[1][1], 500 * 1.0001 * (1 + 0.01 - 0.001))
        self.assertAlmostEqual(path[2][1], path[1][1] * (1 - 0.001))

    def test_event_engine_drops_missing_and_cheap(self):
        spy = {"d": weekdays("2020-01-01", 30), "a": [100 + i for i in range(30)], "c": [100] * 30}
        stock = {"d": spy["d"], "a": [10 * (1.01 ** i) for i in range(30)], "c": [10] * 30}
        cheap = dict(stock, c=[1] * 30)
        get = {"AAA": stock, "BBB": cheap}.get
        res = ins.run_events([("2020-01-01", "1", "AAA"), ("2020-01-01", "2", "BBB"), ("2020-01-01", "3", "ZZZ")],
                             spy, {}, hold=5, cost_bps=0, split="2030-01-01", get=get)
        self.assertEqual(res["dropped"]["too_cheap"], 1)
        self.assertEqual(res["dropped"]["no_prices"], 1)
        self.assertEqual(res["in_sample"]["events"], 1)


if __name__ == "__main__":
    unittest.main()
