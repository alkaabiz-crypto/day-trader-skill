import unittest

from _load import load

sv = load("trader-lab", "survivors")


class Survivors(unittest.TestCase):
    def test_signals(self):
        self.assertTrue(sv.entry_signal(5.0, True, False))
        self.assertTrue(sv.entry_signal(40.0, True, True))
        self.assertFalse(sv.entry_signal(5.0, False, True))          # below the 200-day: never
        self.assertTrue(sv.exit_signal(75.0, False, 1))
        self.assertTrue(sv.exit_signal(50.0, True, 1))
        self.assertTrue(sv.exit_signal(50.0, False, 10))
        self.assertFalse(sv.exit_signal(50.0, False, 3))

    def test_features_uptrend_dip(self):
        c = [100 + 0.1 * i for i in range(230)] + [118.0, 117.0]
        r2, above, low7, high7 = sv.features(c)
        self.assertTrue(above[-1])
        self.assertTrue(low7[-1])
        self.assertLess(r2[-1], 10)
        self.assertTrue(high7[229])


if __name__ == "__main__":
    unittest.main()
