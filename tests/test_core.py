import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'kromek_driver'))
from kromek_driver.core import CHANNELS, Snapshot, validate_snapshot, make_interval


def snap(count, ms, live):
    return Snapshot((count,) + (0,) * (CHANNELS - 1), count, ms, live)


class CheckCore(unittest.TestCase):
    def test_consistent(self):
        i = make_interval(snap(100, 1000, 990), snap(225, 2000, 1980))
        self.assertEqual(i.total, 125)
        self.assertAlmostEqual(i.cps_real, 125)
        self.assertAlmostEqual(i.cps_live, 125 * 1000 / 990)
        self.assertEqual(sum(i.counts), 125)

    def test_zero_valid(self):
        i = make_interval(snap(20, 1000, 990), snap(20, 2000, 1990))
        self.assertEqual(i.total, 0)
        self.assertEqual(i.cps_real, 0.0)

    def test_bad_sum(self):
        with self.assertRaises(ValueError):
            validate_snapshot(Snapshot((0,) * CHANNELS, 1, 1000, 990))

    def test_reset(self):
        with self.assertRaises(ValueError):
            make_interval(snap(100, 1000, 990), snap(30, 200, 195))

    def test_channel_regression(self):
        before = Snapshot((3, 0) + (0,) * (CHANNELS - 2), 3, 1000, 990)
        after = Snapshot((2, 2) + (0,) * (CHANNELS - 2), 4, 2000, 1990)
        with self.assertRaises(ValueError):
            make_interval(before, after)


if __name__ == '__main__':
    unittest.main()


class CheckVendorProtections(unittest.TestCase):
    def test_rejects_vendor_invalid_live_time(self):
        from kromek_driver.core import INVALID_TIME_THRESHOLD, has_invalid_time
        abnormal = snap(0, 1000, INVALID_TIME_THRESHOLD)
        self.assertTrue(has_invalid_time(abnormal))
        with self.assertRaises(ValueError):
            validate_snapshot(abnormal)

    def test_rejects_vendor_invalid_real_time(self):
        from kromek_driver.core import INVALID_TIME_THRESHOLD, has_invalid_time
        abnormal = snap(0, INVALID_TIME_THRESHOLD, 1000)
        self.assertTrue(has_invalid_time(abnormal))
        with self.assertRaises(ValueError):
            validate_snapshot(abnormal)

    def test_rejects_regression_after_invalid_read(self):
        with self.assertRaises(ValueError):
            make_interval(snap(200, 2000, 1988), snap(100, 1000, 995))

    def test_cumulative_zero_counts_is_valid(self):
        i = make_interval(snap(0, 1000, 1000), snap(0, 2000, 2000))
        self.assertEqual(i.total, 0)
        self.assertEqual(i.cps_real, 0.0)

    def test_current_live_counter_invalid(self):
        with self.assertRaises(ValueError):
            make_interval(snap(0, 1000, 990), snap(10, 2000, 2200))
