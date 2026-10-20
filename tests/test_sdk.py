"""Mock the vendor ABI to verify our Python function signatures; no hardware needed."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'kromek_driver'))
from kromek_driver.sdk import KromekSDK
from kromek_driver.core import CHANNELS


class NativeFunction:
    def __init__(self, func):
        self.func = func
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.func(*args)


class FakeNativeLibrary:
    def __init__(self, init_rc=0):
        self.initialized = False
        self.started = False
        self.cleared = False
        self.destroyed = False

        def init(*_):
            self.initialized = init_rc == 0
            return init_rc

        def read(_, buffer, total, real, live):
            buffer[3] = 4
            buffer[7] = 6
            total._obj.value = 10
            real._obj.value = 1010
            live._obj.value = 1009
            return 0

        def version(a, b, c, d):
            for ptr, v in zip((a, b, c, d), (16, 3, 9, 24)):
                ptr._obj.value = v

        exports = {
            'kr_GetVersionInformation': version,
            'kr_Initialise': init,
            'kr_GetNextDetector': lambda _prev: 2312687652,
            'kr_ClearAcquiredData': lambda _device: self._clear(),
            'kr_BeginDataAcquisition': lambda _device, real, live: self._begin(real, live),
            'kr_GetAcquiredData': read,
            'kr_IsAcquiringData': lambda _device: 1 if self.started else 0,
            'kr_StopDataAcquisition': lambda _device: self._stop(),
            'kr_Destruct': lambda: self._destruct(),
        }
        for name, fn in exports.items():
            setattr(self, name, NativeFunction(fn))

    def _clear(self):
        self.cleared = True
        return 0

    def _begin(self, real, live):
        assert (real, live) == (0, 0)
        self.started = True
        return 0

    def _stop(self):
        self.started = False
        return 0

    def _destruct(self):
        self.destroyed = True


class TestSDKABI(unittest.TestCase):
    def test_complete_sdk_lifecycle(self):
        fake = FakeNativeLibrary()
        with patch('kromek_driver.sdk.ct.CDLL', return_value=fake):
            sdk = KromekSDK('/tmp/fake_kromek.so')
            self.assertEqual(sdk.version(), '16.3.9.24')
            self.assertEqual(sdk.start(), 2312687652)
            self.assertTrue(fake.initialized and fake.cleared and fake.started)
            sample = sdk.snapshot()
            self.assertEqual(len(sample.counts), CHANNELS)
            self.assertEqual(sample.total, 10)
            self.assertEqual(sample.counts[3], 4)
            self.assertEqual(sample.counts[7], 6)
            self.assertEqual((sample.real_ms, sample.live_ms), (1010, 1009))
            sdk.close()
            self.assertTrue(fake.destroyed)
            self.assertFalse(fake.started)

    def test_failed_initialization(self):
        fake = FakeNativeLibrary(init_rc=7)
        with patch('kromek_driver.sdk.ct.CDLL', return_value=fake):
            sdk = KromekSDK('/tmp/fake_kromek.so')
            with self.assertRaisesRegex(RuntimeError, 'kr_Initialise returned 7'):
                sdk.start()
            sdk.close()
            self.assertFalse(fake.started)


if __name__ == '__main__':
    unittest.main()
