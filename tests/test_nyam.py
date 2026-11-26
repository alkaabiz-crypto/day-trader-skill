import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import nyam  # noqa: E402


def day(events):
    """Flat 100 candles 05:00-16:00 with range 99-101 before 09:00; `events` = {slot: (o, h, l, c)} after."""
    b = {}
    for s in range(nyam.RANGE_FROM, nyam.CLOSE_SLOT + 1):
        b[s] = (100.0, 100.2, 99.8, 100.0)
    b[nyam.RANGE_FROM] = (100.0, 101.0, 99.0, 100.0)
    b.update(events)
    return b


S = nyam.RANGE_TO   # 09:00


class Nyam(unittest.TestCase):
    def test_reversal_after_up_sweep(self):
        b = day({S: (100.5, 101.6, 100.4, 101.3),          # closes above 101: up-break
                 S + 1: (101.3, 101.5, 101.1, 101.4),
                 S + 2: (101.45, 101.5, 100.6, 100.7),      # red engulfing, back below 101: short at 100.7
                 S + 3: (100.7, 100.7, 98.5, 98.6)})        # stop 101.6 (risk 0.9), target 100.7 - 1.8 = 98.9
        b[S + 2 - 9] = (100.9, 101.0, 100.8, 100.9)          # 45 minutes earlier it was higher: the check agrees
        side, e, x, why = nyam.day_trade(b, "reversal")
        self.assertEqual((side, e, why), (-1, 100.7, "target"))
        self.assertAlmostEqual(x, 98.9)

    def test_continuation_after_up_break(self):
        b = day({S: (100.5, 101.6, 100.4, 101.3),
                 S + 1: (101.3, 101.35, 101.0, 101.1),       # small red
                 S + 2: (101.05, 101.8, 101.0, 101.7),       # green engulfing above 101: long at 101.7, stop 101.0
                 S + 3: (101.7, 103.2, 101.6, 103.1)})       # target 101.7 + 1.4 = 103.1
        side, e, x, why = nyam.day_trade(b, "continuation")
        self.assertEqual((side, why), (1, "target"))
        self.assertAlmostEqual(x, 103.1)

    def test_no_break_no_trade(self):
        self.assertIsNone(nyam.day_trade(day({}), "reversal"))

    def test_45_minute_check_blocks(self):
        events = {S - 9 + 2: (100, 100.2, 99.8, 100.0)}
        b = day({S: (100.5, 101.6, 100.4, 101.3), S + 1: (101.3, 101.5, 101.1, 101.4),
                 S + 2: (101.45, 101.5, 100.6, 100.7)})
        b[S + 2 - 9] = (100, 100.2, 99.0, 99.5)              # 45 minutes earlier the close was lower: a short disagrees
        self.assertIsNone(nyam.day_trade(b, "reversal"))
        del events

    def test_frozen(self):
        self.assertEqual((nyam.RANGE_FROM, nyam.RANGE_TO, nyam.SIGNAL_TO, nyam.CHECK_BARS, nyam.TARGET_R,
                          nyam.COST_BPS, nyam.SPLIT, nyam.T_BAR), (60, 108, 144, 9, 2.0, 20.0, "2025-01-01", 3.0))


if __name__ == "__main__":
    unittest.main()
