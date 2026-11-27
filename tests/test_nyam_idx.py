import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import candles  # noqa: E402
import nyam_idx  # noqa: E402


class NyamIdx(unittest.TestCase):
    def build(self, skip):
        base = 1795600800 - 86400 - 3600  # 2026-11-24T09:00:00Z = 04:00 New York (standard time)
        bars = {}
        for i in range(145):              # 04:00 .. 16:00
            if i in skip:
                continue
            p = 100 + i / 100
            bars[str(base + 300 * i)] = [p, p, p, p]
        with tempfile.TemporaryDirectory() as d:
            old = nyam_idx.STORE
            nyam_idx.STORE = d
            try:
                candles.save_gz(nyam_idx.path("spy"), bars)
                return nyam_idx.idx_days("spy")
            finally:
                nyam_idx.STORE = old

    def test_thin_premarket_is_filled(self):
        skip = set(range(13, 40))          # 27 of the 48 range candles (05:00-08:55 = i 12..59) missing -> 21 left
        self.assertEqual(self.build(skip), {})
        skip = set(range(13, 35))          # 22 missing -> 26 left: counts, gaps filled flat
        b = self.build(skip)["2026-11-24"]
        self.assertEqual(b[61], (b[60][3],) * 4)

    def test_no_candle_before_0500_skips(self):
        self.assertEqual(self.build(set(range(0, 14))), {})   # first candle 05:10: nothing to fill 05:00 from

    def test_regular_hours_must_be_there(self):
        self.assertEqual(self.build(set(range(70, 75))), {})   # 5 regular-hours candles missing

    def test_frozen(self):
        self.assertEqual((nyam_idx.SYMBOLS, nyam_idx.START, nyam_idx.COST_BPS, nyam_idx.MIN_REGULAR, nyam_idx.MIN_RANGE),
                         (["spy", "qqq"], "2016-01-01", 5.0, 75, 24))


if __name__ == "__main__":
    unittest.main()
