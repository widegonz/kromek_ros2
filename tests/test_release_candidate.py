import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'kromek_driver'))
from kromek_driver.recovery import next_deadline
from kromek_driver.sdk import KromekSDK
from test_sdk import FakeNativeLibrary, NativeFunction


class TestSchedule(unittest.TestCase):
    def test_no_drift_after_late_poll(self):
        self.assertAlmostEqual(next_deadline(11.0, 11.05, 1.0), 12.0)
        self.assertAlmostEqual(next_deadline(12.0, 12.01, 1.0), 13.0)

    def test_skip_missed_slots(self):
        self.assertAlmostEqual(next_deadline(11.0, 13.3, 1.0), 14.0)

    def test_no_change_if_not_due(self):
        self.assertAlmostEqual(next_deadline(11.0, 10.5, 1.0), 11.0)

    def test_bad_period(self):
        with self.assertRaises(ValueError):
            next_deadline(11, 12, 0)


class TestShutdown(unittest.TestCase):
    def test_ignores_stop_when_known_disconnected(self):
        fake = FakeNativeLibrary()
        fake.kr_StopDataAcquisition = NativeFunction(lambda dev: (_ for _ in ()).throw(AssertionError('STOP should not be called')))
        with patch('kromek_driver.sdk.ct.CDLL', return_value=fake):
            sdk = KromekSDK('/tmp/fake_sdk.so')
            sdk.start()
            warning = sdk.close(disconnected=True)
            self.assertTrue(warning)
            self.assertTrue(fake.destroyed)

    def test_invalid_id_warns_and_destroys(self):
        fake = FakeNativeLibrary()
        fake.kr_StopDataAcquisition = NativeFunction(lambda dev: 7)
        with patch('kromek_driver.sdk.ct.CDLL', return_value=fake):
            sdk = KromekSDK('/tmp/fake_sdk.so')
            sdk.start()
            warning = sdk.close()
            self.assertTrue(any('7' in x for x in warning))
            self.assertTrue(fake.destroyed)

    def test_unexpected_stop_error(self):
        fake = FakeNativeLibrary()
        fake.kr_StopDataAcquisition = NativeFunction(lambda dev: 3)
        with patch('kromek_driver.sdk.ct.CDLL', return_value=fake):
            sdk = KromekSDK('/tmp/fake_sdk.so')
            sdk.start()
            with self.assertRaisesRegex(RuntimeError, 'returned 3'):
                sdk.close()
            self.assertTrue(fake.destroyed)
