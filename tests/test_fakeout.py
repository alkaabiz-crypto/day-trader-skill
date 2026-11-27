import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import fakeout as fk  # noqa: E402


def session(path):
    bars = [{"o": o, "h": h, "l": l, "c": c, "v": 100} for o, h, l, c in path]
    last = bars[-1]["c"]
    while len(bars) < 78:
        bars.append({"o": last, "h": last, "l": last, "c": last, "v": 100})
    return bars


FIRST = (100, 101, 99.8, 100.9)          # green first candle: long, level 101, height 1.2


class Fakeout(unittest.TestCase):
    def test_stop_entry_fake(self):
        b = session([FIRST, (100.9, 101.2, 100.95, 101.1), (101.1, 101.1, 99.7, 99.9)])
        slot, px, x, why = fk.stop_entry(b, 1, 101, 1.2)
        self.assertEqual((slot, px, why), (1, 101, "stop"))
        self.assertAlmostEqual(x, 99.8)

    def test_stop_entry_holds_to_close(self):
        b = session([FIRST, (100.9, 101.5, 100.95, 101.4), (101.4, 103, 101.3, 102.8)])
        self.assertEqual(fk.stop_entry(b, 1, 101, 1.2)[3], "close")

    def test_close_confirm_skips_a_wick_through(self):
        # candle 1 pokes above 101 but closes below: the stop order fills, the close rule waits
        b = session([FIRST, (100.9, 101.3, 100.5, 100.7), (100.7, 100.8, 99.5, 99.6)])
        self.assertEqual(fk.stop_entry(b, 1, 101, 1.2)[3], "stop")
        self.assertIsNone(fk.confirm_entry(b, 1, 101, 1.2))

    def test_flags_have_no_lookahead(self):
        b = session([FIRST])
        f = fk.flags_of("AAPL", b, 1, 6.0, 3.0, 97.0, {"o": 10, "c": 9}, 1)
        self.assertTrue(f["market_against"] and f["tiny_candle"] and f["big_gap"] and f["extreme_rvol"] and f["instant_fill"])
        self.assertFalse(f["weak_close"] or f["late_fill"])

    def test_frozen(self):
        self.assertEqual((fk.TOP, fk.MIN_RVOL, fk.LOOKBACK, fk.SPLIT, fk.T_BAR, len(fk.FLAGS)),
                         (5, 1.5, 14, "2025-01-01", 3.0, 7))


if __name__ == "__main__":
    unittest.main()
