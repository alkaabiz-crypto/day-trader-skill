import unittest

from _load import load

try:
    import numpy as np
    fa = load("trader-lab", "factors")
    fe = load("trader-lab", "factor_etfs")
except ImportError:          # numpy is optional (research script only)
    np = None

CSV = """This file was created using the 202609 CRSP database.

,Mkt-RF,SMB,HML,RF
192607,   2.89,  -2.42,  -2.75,   0.22
192608,   2.64,  -1.20,   4.18,   0.25

 Annual Factors: January-December
,Mkt-RF,SMB,HML,RF
1927,  29.47,  -2.46,  -3.75,   3.12
"""


@unittest.skipIf(np is None, "numpy not installed")
class Factors(unittest.TestCase):
    def test_parse_reads_only_the_monthly_block(self):
        cols, rows = fa.parse_monthly(CSV)
        self.assertEqual(cols, ["Mkt-RF", "SMB", "HML", "RF"])
        self.assertEqual(sorted(rows), ["1926-07", "1926-08"])
        self.assertEqual(rows["1926-08"][2], 4.18)

    def test_newey_west_t_matches_plain_t_on_white_noise_scale(self):
        x = np.random.default_rng(1).normal(0.5, 1.0, 5000)
        plain = x.mean() / x.std(ddof=1) * np.sqrt(len(x))
        self.assertAlmostEqual(fa.nw_t(x) / plain, 1.0, delta=0.05)

    def test_a_fund_that_is_spy_has_no_alpha(self):
        rng = np.random.default_rng(2)
        months = ["%d-%02d" % (2000 + i // 12, i % 12 + 1) for i in range(120)]
        spy = {m: (float(r), 0.001) for m, r in zip(months, rng.normal(0.008, 0.04, 120))}
        r = fe.compare(dict(spy), spy)
        self.assertAlmostEqual(r["beta"], 1.0)
        self.assertAlmostEqual(r["alpha_pct_year"], 0.0, places=9)
        self.assertAlmostEqual(r["cagr"], r["spy_cagr"])


if __name__ == "__main__":
    unittest.main()
