import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import crypto_xs as cx  # noqa: E402


def coin(start, n, growth, vol=1e7):
    d0 = datetime.date.fromisoformat(start)
    return {(d0 + datetime.timedelta(days=k)).isoformat(): (100 * growth ** k, vol) for k in range(n)}


class CryptoXS(unittest.TestCase):
    def test_frozen_design(self):
        self.assertEqual((cx.FORM_WEEKS, cx.MIN_COINS, cx.COST_BPS, cx.SPLIT, cx.T_BAR),
                         (3, 9, 25.0, "2021-01-01", 3.0))

    def test_eligibility_needs_full_history_and_volume(self):
        t0 = datetime.date(2020, 3, 1)
        self.assertIsNotNone(cx.eligible(coin("2020-01-01", 120, 1.01), t0))
        self.assertIsNone(cx.eligible(coin("2020-02-20", 60, 1.01), t0))           # too young
        self.assertIsNone(cx.eligible(coin("2020-01-01", 120, 1.01, vol=1.0), t0))  # too illiquid

    def test_dead_coin_valued_at_last_close(self):
        px = coin("2020-01-01", 62, 1.0)  # stops on 2020-03-02
        self.assertAlmostEqual(cx.hold_return(px, datetime.date(2020, 3, 1)), 0.0)

    def test_momentum_wins_when_trends_persist(self):
        data = {"C%d" % i: coin("2019-01-06", 400, 1 + (i - 6) * 0.001) for i in range(12)}
        wk = cx.weeks(data)
        self.assertTrue(wk)
        dates, h1, h2 = cx.series(wk, 0.0)
        self.assertTrue(all(x > 0 for x in h1))
        self.assertTrue(all(x > 0 for x in h2))


if __name__ == "__main__":
    unittest.main()
