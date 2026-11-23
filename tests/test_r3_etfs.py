import unittest

from _load import load

r3e = load("trader-lab", "r3_etfs")


class FreshEtfSet(unittest.TestCase):
    def test_new_set_excludes_the_lab_etfs(self):
        self.assertFalse(set(r3e.NEW_ETFS) & set(r3e.OLD_ETFS))

    def test_no_duplicates_and_no_leveraged_in_test_set(self):
        self.assertEqual(len(r3e.NEW_ETFS), len(set(r3e.NEW_ETFS)))
        self.assertFalse(set(r3e.NEW_ETFS) & set(r3e.LEVERAGED))

    def test_placebo_keeps_trade_count_and_lengths(self):
        D = {"d": ["2020-01-%02d" % (i % 28 + 1) for i in range(400)],
             "o": [100.0 + i * 0.1 for i in range(400)], "h": [0] * 400, "l": [0] * 400,
             "c": [100.0 + i * 0.1 for i in range(400)], "v": [1] * 400}
        D["d"] = ["%04d-%02d-%02d" % (2000 + i // 300, i // 25 % 12 + 1, i % 25 + 1) for i in range(400)]
        tb = {"X": [(250, 255, 0.0, D["o"][251]), (300, 302, 0.0, D["o"][301])]}
        ev = r3e.evaluate({"X": D}, tb, reps=5)
        self.assertIn("full", ev)
        self.assertTrue(0 < ev["full"]["p"] <= 1)
        self.assertGreater(ev["full"]["t"], 0)  # a steadily rising price: long trades make money


if __name__ == "__main__":
    unittest.main()
