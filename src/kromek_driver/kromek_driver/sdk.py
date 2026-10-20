"""Kromek SIGMA50 native SDK bindings (Dr. Park's vendor archive).

Bindings match SpectrometerDriver.h. The SDK is NOT bundled in this ROS
package. Use the library compiled on the destination robot (ARM64/Foxy).
"""
import ctypes as ct
from pathlib import Path
from .core import CHANNELS, Snapshot


class KromekSDK:
    def __init__(self, library_path):
        self.library_path = str(Path(library_path).expanduser().resolve())
        lib = ct.CDLL(self.library_path)

        def bind(name, argtypes, restype=ct.c_int):
            fn = getattr(lib, name)
            fn.argtypes = argtypes
            fn.restype = restype
            return fn

        uptr = ct.POINTER(ct.c_uint)
        iptr = ct.POINTER(ct.c_int)
        self._version = bind('kr_GetVersionInformation', [iptr] * 4, None)
        self._init = bind('kr_Initialise', [ct.c_void_p, ct.c_void_p])
        self._next = bind('kr_GetNextDetector', [ct.c_uint], ct.c_uint)
        self._clear = bind('kr_ClearAcquiredData', [ct.c_uint])
        self._begin = bind('kr_BeginDataAcquisition', [ct.c_uint, ct.c_uint, ct.c_uint])
        self._read = bind('kr_GetAcquiredData', [ct.c_uint, uptr, uptr, uptr, uptr])
        self._is_acquiring = bind('kr_IsAcquiringData', [ct.c_uint])
        self._stop = bind('kr_StopDataAcquisition', [ct.c_uint])
        self._destruct = bind('kr_Destruct', [], None)
        self._initialized = False
        self._started = False
        self.device_id = 0

    def version(self):
        values = [ct.c_int() for _ in range(4)]
        self._version(*(ct.byref(v) for v in values))
        return '.'.join(str(v.value) for v in values)

    def start(self):
        self._check(self._init(None, None), 'kr_Initialise')
        self._initialized = True
        self.device_id = self._next(0)
        if not self.device_id:
            raise RuntimeError('No Kromek detector returned by SDK')
        self._check(self._clear(self.device_id), 'kr_ClearAcquiredData')
        # The vendor scripts use unlimited acquisition; not the SDK timer.
        self._check(self._begin(self.device_id, 0, 0), 'kr_BeginDataAcquisition')
        self._started = True
        return self.device_id

    @staticmethod
    def _check(rc, name):
        if rc != 0:
            raise RuntimeError('{} returned {}'.format(name, rc))

    def snapshot(self):
        if not self._started:
            raise RuntimeError('Acquisition was not started')
        # SpectrometerData.h defines TOTAL_RESULT_CHANNELS=4096.
        # Detector.cpp copies exactly that many uint32 values.
        buffer = (ct.c_uint * CHANNELS)()
        total = ct.c_uint()
        real_ms = ct.c_uint()
        live_ms = ct.c_uint()
        self._check(
            self._read(self.device_id, buffer, ct.byref(total),
                       ct.byref(real_ms), ct.byref(live_ms)),
            'kr_GetAcquiredData')
        if self._is_acquiring(self.device_id) != 1:
            raise RuntimeError('SDK reports acquisition stopped')
        return Snapshot(tuple(int(x) for x in buffer), int(total.value),
                        int(real_ms.value), int(live_ms.value))

    def close(self, disconnected=False):
        """Release SDK resources, even if a USB unplug invalidated device ID.

        Return cleanup warnings rather than hiding INVALID_DEVICE_ID (7).
        If the USB device is known to be gone, avoid sending STOP to it.
        Non-7 STOP errors propagate after kr_Destruct has run.
        """
        warnings = []
        stop_error = None
        try:
            if self._started:
                self._started = False
                if disconnected:
                    warnings.append('Skipped kr_StopDataAcquisition: USB disconnected')
                else:
                    code = self._stop(self.device_id)
                    if code == 7:  # ERROR_INVALID_DEVICE_ID in SpectrometerData.h
                        warnings.append('kr_StopDataAcquisition returned 7 (invalid device ID)')
                    elif code != 0:
                        stop_error = RuntimeError(
                            'kr_StopDataAcquisition returned {}'.format(code))
        finally:
            if self._initialized:
                self._initialized = False
                self._destruct()
            self.device_id = 0
        if stop_error:
            raise stop_error
        return warnings
