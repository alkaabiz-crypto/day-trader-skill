import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import alloc  # noqa: E402


class Alloc(unittest.TestCase):
    def test_parse_prefers_adjusted_close(self):
        doc = {"chart": {"result": [{"meta": {"gmtoffset": -18000}, "timestamp": [1262613600, 1262700000],
                                     "indicators": {"quote": [{"close": [10.0, 11.0]}],
                                                    "adjclose": [{"adjclose": [9.0, 10.0]}]}}]}}
        D = alloc.parse_adj(json.dumps(doc))
        self.assertEqual(D["c"], [9.0, 10.0])
        self.assertEqual(D["d"], ["2010-01-04", "2010-01-05"])

    def test_month_ends(self):
        d = ["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-28", "2020-03-02"]
        self.assertEqual(alloc.month_ends(d), [1, 3, 4])

    def test_value_on_uses_last_known_close(self):
        D = {"d": ["2020-01-02", "2020-01-06"], "c": [1.0, 2.0]}
        self.assertEqual(alloc.value_on(D, "2020-01-03"), 1.0)
        self.assertIsNone(alloc.value_on(D, "2019-12-31"))

    def test_bootstrap_p_identical_series_is_not_significant(self):
        xs = [0.01 * ((i * 7) % 5 - 2) for i in range(60)]
        self.assertEqual(alloc.boot_p(xs, xs, draws=200), 1.0)
        better = [x + 0.02 for x in xs]
        self.assertLess(alloc.boot_p(better, xs, draws=200), 0.05)


if __name__ == "__main__":
    unittest.main()
