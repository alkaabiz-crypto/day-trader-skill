import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import sip_forward as sf  # noqa: E402


class SipForward(unittest.TestCase):
    def test_frozen_rule_and_date(self):
        self.assertEqual(sf.FREEZE, "2026-11-24")
        self.assertEqual(sf.PARAMS, {"min_rvol": 1.5, "stop": "bar", "top": 5})
        self.assertEqual(sf.MIN_DAYS, 60)

    def test_verdict_waits_for_60_sessions(self):
        self.assertEqual(sf.verdict(59, 50.0, 9.0), "FORWARD-TEST")
        self.assertEqual(sf.verdict(60, 5.0, 2.1), "PROMOTE")
        self.assertEqual(sf.verdict(60, 5.0, 1.9), "FAIL")
        self.assertEqual(sf.verdict(80, -1.0, 2.5), "FAIL")

    def test_nothing_on_or_before_the_freeze_is_scored(self):
        dates, series, n = sf.forward_series({}, 5.0)
        self.assertEqual((dates, series, n), ([], [], 0))


if __name__ == "__main__":
    unittest.main()
