import unittest

from _load import load

oil_data = load("trader-lab/oilbrain", "oil_data")
brain = load("trader-lab/oilbrain", "brain")


class Data(unittest.TestCase):
    def test_parse_weekly(self):
        html = ("<tr> <td class='B6'>&nbsp;&nbsp;1982-Oct</td> <td class='B5'>10/01&nbsp;</td> "
                "<td class='B3'>334,786&nbsp;&nbsp;&nbsp;</td> <td class='B5'>10/08&nbsp;</td> "
                "<td class='B3'>335,260&nbsp;</td> <td class='B5'>&nbsp;</td> <td class='B3'>&nbsp;</td> </tr>")
        self.assertEqual(oil_data.parse_weekly(html), {"1982-10-01": 334786.0, "1982-10-08": 335260.0})

    def test_parse_cot(self):
        rows = [{"report_date_as_yyyy_mm_dd": "2026-11-17T00:00:00.000", "m_money_positions_long_all": "150",
                 "m_money_positions_short_all": "50", "prod_merc_positions_long": "10",
                 "prod_merc_positions_short": "30", "open_interest_all": "1000"}, {"bad": 1}]
        self.assertEqual(oil_data.parse_cot(rows), {"2026-11-17": {"mm_net": 100.0, "pm_net": -20.0, "oi": 1000.0}})

    def test_publication_lag(self):
        self.assertEqual(oil_data.available("2026-11-13", oil_data.EIA_LAG_DAYS), "2026-11-19")   # Fri -> Thu
        self.assertEqual(oil_data.available("2026-11-17", oil_data.COT_LAG_DAYS), "2026-11-23")   # Tue -> Mon


class Features(unittest.TestCase):
    def test_surprise_against_five_years(self):
        import datetime
        d0 = datetime.date(2000, 1, 7)
        weekly = {(d0 + datetime.timedelta(weeks=k)).isoformat(): float(k) for k in range(320)}   # +1 a week
        s = brain.surprise_series(weekly)
        self.assertTrue(all(abs(v) < 1e-12 for _, v in s))          # a normal week is no surprise
        weekly[max(weekly)] += 10
        self.assertAlmostEqual(brain.surprise_series(weekly)[-1][1], 10.0)

    def test_as_of_has_no_look_ahead(self):
        f = brain.as_of([("2026-11-13", 1.0), ("2026-11-20", 2.0)], 6)
        self.assertIsNone(f("2026-11-18"))
        self.assertEqual(f("2026-11-19"), 1.0)
        self.assertEqual(f("2026-11-25"), 1.0)
        self.assertEqual(f("2026-11-26"), 2.0)

    def test_cot_percentile_and_change(self):
        cot = {"2026-%02d-01" % m: {"mm_net": float(m), "oi": 10.0} for m in range(1, 13)}
        pct, chg = brain.cot_series(cot, window=4)
        self.assertEqual(pct[-1][1], 1.0)
        self.assertAlmostEqual(chg[-1][1], 0.4)

    def test_zscore_uses_only_the_past(self):
        xs = [float(k % 7) for k in range(200)]
        z = brain.zscore(xs, win=50, minn=20)
        z2 = brain.zscore(xs[:150] + [99.0] * 50, win=50, minn=20)
        self.assertEqual(z[:150], z2[:150])
        self.assertIsNone(z[10])


class Costs(unittest.TestCase):
    def test_side_changes_and_nights(self):
        net = brain.run([1, 1, -1, 0, 1], [0.01, 0.01, 0.01, 0.01, 0.0], [1, 3, 1, 1, 1])
        self.assertAlmostEqual(net[0], 0.01 - 0.0005 - 0.0001)
        self.assertAlmostEqual(net[1], 0.01 - 0.0003)
        self.assertAlmostEqual(net[2], -0.01 - 0.0005 - 0.0001)
        self.assertEqual(net[3], 0.0)
        self.assertAlmostEqual(net[4], -0.0005 - 0.0001)


if __name__ == "__main__":
    unittest.main()
