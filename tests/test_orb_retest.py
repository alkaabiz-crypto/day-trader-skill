import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import orb_retest as orr  # noqa: E402


def session(path):
    """path: list of (o, h, l, c); padded to 78 flat candles at the last close."""
    bars = [{"o": o, "h": h, "l": l, "c": c} for o, h, l, c in path]
    last = bars[-1]["c"]
    while len(bars) < 78:
        bars.append({"o": last, "h": last, "l": last, "c": last})
    return bars


RANGE = [(100, 101, 99, 100.5), (100.5, 101, 100, 100.8), (100.8, 101, 100.2, 100.9)]   # range 99-101, height 2


class OrbRetest(unittest.TestCase):
    def test_break_retest_target(self):
        b = session(RANGE + [(100.9, 101.6, 100.9, 101.5),      # break and close above 101
                             (101.5, 101.6, 100.95, 101.2),     # retest touches 101: buy at 101
                             (101.2, 102.6, 101.1, 102.5)])     # 3R target = 101 + 3 x 0.5 = 102.5
        side, e, x, why = orr.day_trade(b, 3.0)
        self.assertEqual((side, e, x, why), (1, 101, 102.5, "target"))

    def test_no_retest_no_trade(self):
        b = session(RANGE + [(100.9, 101.6, 100.9, 101.5), (101.5, 103, 101.4, 102.9)])
        self.assertIsNone(orr.day_trade(b, 3.0))

    def test_stop_inside_the_range_and_stop_wins_ties(self):
        b = session(RANGE + [(100.9, 101.6, 100.9, 101.5),
                             (101.5, 101.6, 100.4, 100.6)])     # touches 101 and the 100.5 stop in one candle
        side, e, x, why = orr.day_trade(b, 3.0)
        self.assertEqual((e, x, why), (101, 100.5, "stop"))

    def test_short_side(self):
        b = session(RANGE + [(100.1, 100.1, 98.6, 98.7),        # close below 99
                             (98.7, 99.05, 98.6, 98.9),         # retest of 99: sell at 99
                             (98.9, 98.9, 97.4, 97.5)])         # target 99 - 1.5 = 97.5
        side, e, x, why = orr.day_trade(b, 3.0)
        self.assertEqual((side, e, x, why), (-1, 99, 97.5, "target"))

    def test_frozen(self):
        self.assertEqual((orr.RANGE_SLOTS, orr.LAST_ENTRY_SLOT, orr.STOP_FRAC, orr.TARGETS[0], orr.SPLIT),
                         (3, 24, 0.25, 3.0, "2025-01-01"))


if __name__ == "__main__":
    unittest.main()
