import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trader-lab"))
import dashboard  # noqa: E402


def read(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


class Dashboard(unittest.TestCase):
    def test_empty_books_still_write_headers(self):
        out = tempfile.mkdtemp()
        n = dashboard.export(out, book_dir=tempfile.mkdtemp(), scoreboard=[])
        self.assertEqual(n, {"equity": 0, "trades": 0, "positions": 0, "scoreboard": 0})
        for f in ("equity.csv", "trades.csv", "positions.csv", "scoreboard.csv"):
            self.assertTrue(os.path.exists(os.path.join(out, f)))

    def test_filled_books(self):
        book, out = tempfile.mkdtemp(), tempfile.mkdtemp()
        with open(os.path.join(book, "equity.csv"), "w") as fh:
            fh.write("time,cash,open,equity\n2026-11-24 10:46,1000,3,10000\n")
        with open(os.path.join(book, "trades.csv"), "w") as fh:
            fh.write("date,symbol,qty,entry_time,entry,stop,target,exit_time,exit,why,gross_usd,cost_usd,pnl_usd\n"
                     "2026-11-24,MSFT,8,2026-11-24 10:46,494.27,490.76,501.29,2026-11-24 12:20,501.29,target,56.17,1.99,54.18\n")
        with open(os.path.join(book, "sip_state.json"), "w") as fh:
            json.dump({"positions": [{"symbol": "AMD", "qty": 10, "entry": 150.0, "side": -1, "stop": 152.0,
                                      "entry_time": "2026-11-25 09:40"}]}, fh)
        dashboard.export(out, book_dir=book, scoreboard=[{"study": "x", "verdict": "FAIL", "detail": "d"}])
        self.assertEqual(read(os.path.join(out, "equity.csv"))[0]["account"], "Breakouts, full market")
        self.assertEqual(read(os.path.join(out, "trades.csv"))[0]["pnl_usd"], "54.18")
        p = read(os.path.join(out, "positions.csv"))[0]
        self.assertEqual((p["account"], p["shares"]), ("Stocks in play", "-10"))   # a short shows negative


if __name__ == "__main__":
    unittest.main()
