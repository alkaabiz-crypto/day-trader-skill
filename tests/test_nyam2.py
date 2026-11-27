import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import nyam  # noqa: E402
import nyam2  # noqa: E402

S = nyam.RANGE_TO   # 09:00, slot 108 (a 45-minute block boundary: 108 = 12 x 9)


def day(events):
    b = {s: (100.0, 100.2, 99.8, 100.0) for s in range(0, nyam.CLOSE_SLOT + 1)}
    b[nyam.RANGE_FROM] = (100.0, 101.0, 99.0, 100.0)
    b.update(events)
    return b


class Nyam2(unittest.TestCase):
    def test_full_engulf_needs_the_wick(self):
        prev = (101.3, 101.5, 101.1, 101.4)
        self.assertTrue(nyam2.full_engulf(prev, (101.45, 101.6, 100.6, 100.7), -1))
        self.assertFalse(nyam2.full_engulf(prev, (101.45, 101.48, 100.6, 100.7), -1))   # high below prev high

    def test_reversal_to_the_opposite_side(self):
        ev = {S: (100.5, 101.6, 100.4, 101.3), S + 1: (101.3, 101.5, 101.1, 101.4),
              S + 2: (101.45, 101.7, 100.6, 100.7),          # full red engulfing: short at 100.7, stop 101.7
              S + 3: (100.7, 100.7, 98.9, 99.0)}             # target = range low 99
        b = day(ev)
        for k in range(S - 9, S):                           # the 45-minute block 08:15-09:00 is red
            b[k] = (100.0, 100.1, 99.85, 99.9)
        b[S - 9] = (100.1, 100.15, 99.9, 100.0)
        side, e, x, why = nyam2.day_trade(b)
        self.assertEqual((side, e, why), (-1, 100.7, "target"))
        self.assertAlmostEqual(x, 99.0)

    def test_45m_block_must_agree(self):
        ev = {S: (100.5, 101.6, 100.4, 101.3), S + 1: (101.3, 101.5, 101.1, 101.4),
              S + 2: (101.45, 101.7, 100.6, 100.7)}
        b = day(ev)
        for k in range(S - 9, S):
            b[k] = (99.9, 100.2, 99.85, 100.1)               # green block: a short is not confirmed
        self.assertIsNone(nyam2.day_trade(b))


if __name__ == "__main__":
    unittest.main()
