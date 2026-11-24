import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import fomc  # noqa: E402

D = datetime.date


class Fomc(unittest.TestCase):
    def test_frozen_design(self):
        self.assertEqual((fomc.FIRST_YEAR, fomc.SPLIT_YEAR, fomc.COST_BPS, fomc.T_BAR), (1994, 2012, 2.0, 3.0))

    def test_historical_page_scheduled_only(self):
        html = ("<h5>January 9 Conference Call - 2008</h5><h5>January 29-30 Meeting - 2008</h5>"
                "<h5>March 2 (unscheduled) Meeting - 2020</h5><h5>March 17-18 (cancelled) Meeting - 2020</h5>"
                "<h5>March 19 (notation vote) - 2020</h5><h5>August 5 Meeting - 2008</h5>")
        self.assertEqual(fomc.parse_historical(html, 2008), [D(2008, 1, 30), D(2008, 8, 5)])

    def test_current_page_and_month_spans(self):
        def blk(m, d):
            return ('<div class="fomc-meeting__month x"><strong>%s</strong></div> '
                    '<div class="fomc-meeting__date y">%s</div>' % (m, d))
        html = ("2024 FOMC Meetings" + blk("Jan/Feb", "31-1") + blk("March", "19-20*") +
                blk("August", "22 (notation vote)") + "2023 FOMC Meetings" + blk("Oct/Nov", "31-1"))
        self.assertEqual(fomc.parse_current(html), [D(2024, 2, 1), D(2024, 3, 20), D(2023, 11, 1)])

    def test_day_returns(self):
        bars = {"SPY": {"d": ["2020-01-02", "2020-01-03"], "o": [100, 101], "c": [100, 102], "a": [100, 102]},
                "_IRX": {"d": ["2020-01-03"], "c": [2.52]}}
        cc, co = fomc.day_returns(bars)["2020-01-03"]
        self.assertAlmostEqual(cc, 0.02 - 0.0252 / 252)
        self.assertAlmostEqual(co, 0.01)


if __name__ == "__main__":
    unittest.main()
