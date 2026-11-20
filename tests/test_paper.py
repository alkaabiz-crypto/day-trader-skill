"""paper/paper.py on the reel's TSLA fixture: 5-minute bars, 60 days to 2026-10-19 10:49 ET."""

import contextlib
import datetime
import io
import json
import os
import shutil
import tempfile
import unittest

from _load import FIX, load

paper = load("paper", "paper")
TSLA = os.path.join(FIX, "trader-timemachine", "TSLA-60d5m.json.gz")


def times(day, start="09:50", end="15:55"):
    t = datetime.datetime.combine(day, datetime.time(9, 50))
    while t.strftime("%H:%M") <= end:
        if t.strftime("%H:%M") >= start:
            yield t
        t += datetime.timedelta(minutes=5)


class Paper(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def tick(self, when):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(paper.main(["tick", "--dir", self.dir, "--offline", TSLA, "--now", when]), 0)
        return buf.getvalue()

    def account(self):
        with open(os.path.join(self.dir, "account.json")) as fh:
            return json.load(fh)

    def test_the_reel_entry_to_the_cent(self):
        self.assertNotIn("BUY", self.tick("2026-10-19 10:12"))  # the 10:10 bar is still forming
        out = self.tick("2026-10-19 10:15")
        self.assertIn("BUY  TSLA 8 sh at $364.18", out)
        p = self.account()["positions"][0]
        self.assertEqual((p["entry"], p["stop"], p["target"], p["shares"]), (364.18, 358.32, 370.04, 8))
        self.assertEqual(self.account()["cash"], 2086.56)
        self.assertIn("HOLD TSLA", self.tick("2026-10-19 10:45"))

    def test_a_late_trigger_is_not_taken(self):
        self.assertNotIn("BUY", self.tick("2026-10-19 10:40"))  # 10:15 breakout, five bars old

    def test_full_days_stop_and_target(self):
        for day in (datetime.date(2026, 10, 13), datetime.date(2026, 10, 15)):
            for t in times(day):
                self.tick(t.strftime("%Y-%m-%d %H:%M"))
        closed = self.account()["closed"]
        self.assertEqual([(c["day"], c["reason"], c["pnl"]) for c in closed],
                         [("2026-10-13", "stop", -31.46), ("2026-10-15", "target", 23.79)])
        self.assertEqual(self.account()["cash"], 4992.33)
        self.assertEqual(self.account()["positions"], [])

    def test_early_close_moves_the_limits_up(self):
        last, flat = paper.limits(paper.DEFAULTS, datetime.date(2026, 11, 27))
        self.assertEqual((last.strftime("%H:%M"), flat.strftime("%H:%M")), ("12:30", "12:55"))
        last, flat = paper.limits(paper.DEFAULTS, datetime.date(2026, 11, 20))
        self.assertEqual((last.strftime("%H:%M"), flat.strftime("%H:%M")), ("15:30", "15:55"))

    def test_run_refuses_a_replay_clock(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(paper.main(["run", "--dir", self.dir, "--now", "2026-10-19 10:15"]), 1)


if __name__ == "__main__":
    unittest.main()
