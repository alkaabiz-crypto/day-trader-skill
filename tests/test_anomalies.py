import unittest

from _load import load

try:
    import numpy as np
    an = load("trader-lab", "anomalies")
except ImportError:          # numpy is optional (research script only)
    np = None


@unittest.skipIf(np is None, "numpy not installed")
class Dash(unittest.TestCase):
    def test_settlement_lag_follows_the_rule_changes(self):
        self.assertEqual(an.settle_lag("2010-05-03"), 3)
        self.assertEqual(an.settle_lag("2017-09-05"), 2)
        self.assertEqual(an.settle_lag("2024-05-28"), 1)

    def test_windows_around_the_selling_day(self):
        d = ["2020-01-%02d" % i for i in (21, 22, 23, 24, 27, 28, 29, 30, 31)] + ["2020-02-03", "2020-02-04", "2020-02-05"]
        avoid, revert = an.dash_positions(d)
        # settlement 2 days in 2020: selling day T-3 = 01-28; flat over the sessions 01-24, 01-27, 01-28
        self.assertEqual(avoid.tolist(), [1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1])
        # long from 01-28's close through the 3rd session of February
        # (the list's first and last days look like a month start / month end, so compare the inside)
        self.assertEqual(revert[2:11].tolist(), [0, 0, 0, 1, 1, 1, 1, 1, 1])


if __name__ == "__main__":
    unittest.main()
