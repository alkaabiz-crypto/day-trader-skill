import os
import tempfile
import unittest

from _load import load

paper = load("trader-lab", "paper")
N = 78

CFG = {"start_date": "2026-01-01", "instruments": {"US500": "SPY", "USTEC": "QQQ", "US30": "DIA"},
       "min_move_pct": 1.0, "stop_pct": 0.5, "no_entries_after": "15:35", "flat_by": "15:55",
       "budget_usd": 1000, "risk_per_trade_usd": 10, "max_daily_loss_usd": 30, "max_trades_per_day": 3,
       "cost_bps": 2.0,
       "pass_bar": {"min_days": 20, "min_trades": 30, "min_t": 2.0, "max_drawdown_usd": 60, "max_demo_lag": 0.30}}


def flat(px, n=N):
    return [{"o": px, "h": px, "l": px, "c": px, "v": 1, "slot": i} for i in range(n)]


class Rule(unittest.TestCase):
    def test_signal_fades_big_moves_only(self):
        self.assertEqual(paper.signal(100.0, 101.2, CFG)[0], -1)    # up 1.2% -> sell
        self.assertEqual(paper.signal(100.0, 98.9, CFG)[0], 1)      # down 1.1% -> buy
        self.assertEqual(paper.signal(100.0, 100.5, CFG)[0], 0)     # 0.5%: no trade

    def test_size_respects_risk_and_no_leverage(self):
        self.assertEqual(paper.size(CFG), 1000)                      # $10/0.5% = $2,000, capped at the budget
        cfg = dict(CFG, budget_usd=5000)
        self.assertEqual(paper.size(cfg), 2000)                      # risk cap binds: max loss $10
        self.assertLessEqual(paper.size(cfg) * cfg["stop_pct"] / 100, cfg["risk_per_trade_usd"])

    def test_tickets_largest_first_within_limits(self):
        prev = {p: flat(100.0) for p in ("SPY", "QQQ", "DIA")}
        day = {"SPY": flat(101.5), "QQQ": flat(97.0), "DIA": flat(100.2)}
        ts = paper.tickets_for(day, prev, CFG)
        self.assertEqual([t["instrument"] for t in ts], ["USTEC", "US500"])   # DIA moved too little
        self.assertEqual([t["side"] for t in ts], ["buy", "sell"])
        self.assertEqual(ts[0]["max_loss_usd"], 5.0)
        tight = dict(CFG, max_daily_loss_usd=10)
        self.assertEqual(len(paper.tickets_for(day, prev, tight)), 1)        # daily risk cap


class Fills(unittest.TestCase):
    def test_exit_at_1555_and_stop(self):
        b = flat(100.0)
        b[76] = dict(b[76], c=100.4)
        e, x, stopped, g = paper.shadow_fill(b, "buy", CFG)
        self.assertEqual((e, x, stopped), (100.0, 100.4, False))
        self.assertAlmostEqual(g, 40.0)
        b[74] = dict(b[74], o=99.8, l=99.3)                                    # trades through 99.5
        e, x, stopped, g = paper.shadow_fill(b, "buy", CFG)
        self.assertTrue(stopped)
        self.assertAlmostEqual(x, 99.5)
        b[74] = dict(b[74], o=99.0, l=98.9)                                    # gaps below the stop
        self.assertEqual(paper.shadow_fill(b, "buy", CFG)[1], 99.0)
        s = flat(100.0)
        s[73] = dict(s[73], h=100.6)
        e, x, stopped, g = paper.shadow_fill(s, "sell", CFG)
        self.assertTrue(stopped)
        self.assertAlmostEqual(g, -50.0)

    def test_log_day_writes_net_of_costs(self):
        prev = flat(100.0)
        day = flat(101.5)
        day[76] = dict(day[76], c=101.3)
        sess = {"SPY": [("2026-01-02", prev), ("2026-01-05", day)]}
        rows = paper.log_day(sess, "2026-01-05", CFG)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["instrument"], r["side"]), ("US500", "sell"))
        self.assertAlmostEqual(r["net_bps"], round((1 - 101.3 / 101.5) * 1e4 - 2.0, 2))
        self.assertAlmostEqual(r["pnl_usd"], round(1000 * r["net_bps"] / 1e4, 2))


class ScannerTrack(unittest.TestCase):
    def bars(self, n=N, px=50.0, rng=0.02):
        return [{"o": px, "h": px + rng, "l": px - rng, "c": px, "v": 1, "slot": i} for i in range(n)]

    def test_plan_sizing_stop_target(self):
        hit = {"symbol": "ABC", "price": 51.0, "or_high": 50.5, "or_low": 49.5, "pct_over": 1.0}
        p = paper.scanner_plan(hit, self.bars(4), {"ABC"})
        self.assertEqual((p["stop"], p["target"]), (50.0, 52.0))
        self.assertEqual(p["shares"], 10)                    # $10 risk / $1 = 10 (19 by budget)
        self.assertTrue(p["premarket_hit"])
        self.assertLessEqual(p["max_loss_usd"], 10.0)

    def test_plan_skips_when_costs_eat_the_reward(self):
        hit = {"symbol": "ABC", "price": 50.06, "or_high": 50.05, "or_low": 49.95, "pct_over": 0.02}
        noisy = self.bars(4, rng=0.3)                        # wide bars: a big spread estimate
        self.assertIsNone(paper.scanner_plan(hit, noisy, set()))

    def test_pick_prefers_premarket_then_fresh(self):
        hits = [{"symbol": "A", "pct_over": 0.2}, {"symbol": "B", "pct_over": 2.0}, {"symbol": "C", "pct_over": 0.1}]
        self.assertEqual([h["symbol"] for h in paper.pick_scanner(hits, {"B"}, 3)], ["B", "C", "A"])

    def test_fill_long_target_stop_and_close(self):
        b = self.bars()
        b[4] = dict(b[4], o=50.0)
        b[10] = dict(b[10], h=52.5)
        self.assertEqual(paper.fill_long(b, 4, 49.0, 52.0), (50.0, 52.0, "target"))
        b[8] = dict(b[8], l=48.9, h=52.5)                   # both in one bar: counted as the stop
        self.assertEqual(paper.fill_long(b, 4, 49.0, 52.0)[2], "stop")
        c = self.bars()
        self.assertEqual(paper.fill_long(c, 4, 49.0, 52.0)[2], "close")
        self.assertEqual(paper.slot_of("09:50"), 4)


class Report(unittest.TestCase):
    def rows(self, nets, start="2026-01-"):
        return [{"date": "%s%02d" % (start, i % 28 + 1) if i < 28 else "2026-02-%02d" % (i - 27),
                 "source": "shadow", "instrument": "US500", "net_bps": str(n), "pnl_usd": str(n / 10.0)}
                for i, n in enumerate(nets)]

    def test_in_progress_until_enough(self):
        r = paper.evaluate(self.rows([10.0] * 5), dict(CFG, _logged_days=[]))
        self.assertEqual(r["verdict"], "IN PROGRESS")

    def test_pass_and_fail(self):
        good = [12.0, 8.0, 10.0, 11.0, 9.0] * 8                                # 40 steady winners
        days = ["2026-01-%02d" % d for d in range(1, 29)]
        self.assertEqual(paper.evaluate(self.rows(good), dict(CFG, _logged_days=days))["verdict"], "PASS")
        bad = [12.0, -14.0] * 20
        self.assertEqual(paper.evaluate(self.rows(bad), dict(CFG, _logged_days=days))["verdict"], "FAIL")

    def test_cost_stress_can_fail_a_thin_edge(self):
        days = ["2026-01-%02d" % d for d in range(1, 29)]
        thin = [3.0, 2.0, 2.5, 3.5, 2.0] * 8          # net 2.6 bp a trade at the assumed 2 bp cost
        cfg = dict(CFG, _logged_days=days)
        self.assertEqual(paper.evaluate(self.rows(thin), cfg)["verdict"], "PASS")
        r = paper.evaluate(self.rows(thin), dict(cfg, stress_cost_bps=5.0))
        self.assertFalse(r["checks"]["stress_net_positive"])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertAlmostEqual(r["break_even_cost_bps"], 4.6)

    def test_journal_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "j.csv")
            paper.append_rows([{"date": "2026-01-05", "source": "demo", "instrument": "US500", "pnl_usd": -3.2}], path)
            paper.append_rows([{"date": "2026-01-06", "source": "shadow-day"}], path)
            got = paper.read_journal(path)
            self.assertEqual([r["source"] for r in got], ["demo", "shadow-day"])
            self.assertEqual(got[0]["pnl_usd"], "-3.2")


if __name__ == "__main__":
    unittest.main()
