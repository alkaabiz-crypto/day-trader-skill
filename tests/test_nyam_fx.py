import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import candles  # noqa: E402
import nyam_fx  # noqa: E402


class NyamFx(unittest.TestCase):
    def test_fill_and_skip(self):
        # 2026-11-24 (Tuesday) New York 05:00 = 10:00 UTC (standard time); build 05:00-16:00 with 3 gaps
        base = 1795600800 - 86400  # 2026-11-24T10:00:00Z
        bars = {}
        for i in range(133):
            if i in (5, 6, 50):
                continue
            bars[str(base + 300 * i)] = [1.0 + i / 1e4, 1.0 + i / 1e4, 1.0 + i / 1e4, 1.0 + i / 1e4]
        with tempfile.TemporaryDirectory() as d:
            old = nyam_fx.STORE
            nyam_fx.STORE = d
            try:
                candles.save_gz(nyam_fx.path("eurusd"), bars)
                days = nyam_fx.fx_days("eurusd")
            finally:
                nyam_fx.STORE = old
        self.assertEqual(list(days), ["2026-11-24"])
        b = days["2026-11-24"]
        self.assertEqual(b[65], (b[64][3],) * 4)          # 05:25 missing -> flat at 05:20's close

    def test_frozen(self):
        self.assertEqual((nyam_fx.PAIRS, nyam_fx.START, nyam_fx.MIN_CANDLES), ({"xauusd": 5.0, "eurusd": 2.0}, "2022-11-01", 125))


if __name__ == "__main__":
    unittest.main()
