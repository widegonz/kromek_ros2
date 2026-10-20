"""SIGMA50 ROS 2 Foxy acquisition with diagnostics and bounded reconnection.

Experimental stage 4: Linux USB hotplug recovery MUST be validated on the real
robot before enabling as a systemd service. Existing ROS message types unchanged.
"""
import os
import resource
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

from kromek_interfaces.msg import RadiationMeasurement, RadiationSpectrum
from .sdk import KromekSDK
from .core import has_invalid_time, validate_snapshot, make_interval
from .recovery import retry_delay, cpu_percentage, next_deadline


class Sigma50Node(Node):
    def __init__(self):
        super().__init__('sigma50_node')
        default_sdk = str(Path('/opt/kromek/lib/libSpectrometerDriver.so'))
        self.declare_parameter('sdk_library', default_sdk)
        self.declare_parameter('device_path', '/dev/kromek0')
        self.declare_parameter('sample_period_s', 1.0)
        self.declare_parameter('startup_timeout_s', 5.0)
        self.declare_parameter('warmup_real_s', 1.0)
        self.declare_parameter('invalid_timeout_s', 5.0)
        self.declare_parameter('reconnect_initial_s', 2.0)
        self.declare_parameter('reconnect_max_s', 30.0)
        self.declare_parameter('frame_id', 'kromek_link')
        self._library = str(self.get_parameter('sdk_library').value)
        self._device_path = str(self.get_parameter('device_path').value)
        self._period = float(self.get_parameter('sample_period_s').value)
        self._startup_timeout = float(self.get_parameter('startup_timeout_s').value)
        self._warmup_ms = int(float(self.get_parameter('warmup_real_s').value) * 1000)
        self._invalid_timeout = float(self.get_parameter('invalid_timeout_s').value)
        self._reconnect_initial = float(self.get_parameter('reconnect_initial_s').value)
        self._reconnect_max = float(self.get_parameter('reconnect_max_s').value)
        self._frame = str(self.get_parameter('frame_id').value)
        if not (self._period >= 0.2 and self._startup_timeout > 0 and
                self._warmup_ms >= 0 and self._invalid_timeout > 0 and
                self._reconnect_initial > 0 and self._reconnect_max >= self._reconnect_initial):
            raise ValueError('Invalid acquisition/reconnection parameters')

        self._measurement_pub = self.create_publisher(RadiationMeasurement, 'measurement', 10)
        self._spectrum_pub = self.create_publisher(RadiationSpectrum, 'spectrum', 5)
        self._diagnostics = self.create_publisher(DiagnosticArray, '/diagnostics', 10)
        self._sdk = None
        self._sdk_version = 'unknown'
        self._device_id = 0
        self._previous = None
        self._state = 'WAITING'
        self._detail = 'Waiting for device'
        self._failures = 0
        self._next_retry = 0.0
        self._startup_deadline = 0.0
        self._next_sample = 0.0
        self._next_diagnostic = 0.0
        self._invalid_since = None
        self._published_count = 0
        self._last_cps = None
        self._last_warning = 0.0
        self._cpu_last_time = time.monotonic()
        self._cpu_last_usage = self._cpu_seconds()
        self._process_cpu_pct = 0.0
        # 50 ms host poll; SDK retains authority over true integration time.
        self._timer = self.create_timer(0.05, self._tick)
        self.get_logger().info('kromek_ros2 RC1 driver ready; SDK={} (not started yet)'.format(
            self._library))

    @staticmethod
    def _cpu_seconds():
        r = resource.getrusage(resource.RUSAGE_SELF)
        return r.ru_utime + r.ru_stime

    def _close_sdk(self, disconnected=False):
        sdk, self._sdk = self._sdk, None
        if sdk is not None:
            try:
                for warning in sdk.close(disconnected=disconnected):
                    self.get_logger().warn('SDK cleanup: {}'.format(warning))
            except Exception as exc:
                self.get_logger().error('SDK cleanup error: {}'.format(exc))
        self._previous = None
        self._device_id = 0

    def _fail(self, error):
        self._state = 'RECOVERING'
        self._detail = str(error)
        self._failures += 1
        self.get_logger().error('Kromek error: {}. Reconnection attempt {}'.format(
            self._detail, self._failures))
        self._close_sdk(disconnected=not Path(self._device_path).exists()
                        or 'USB device node disappeared' in self._detail)
        delay = retry_delay(self._failures, self._reconnect_initial,
                            self._reconnect_max)
        self._next_retry = time.monotonic() + delay
        self._invalid_since = None

    def _connect(self, now):
        if not Path(self._device_path).exists():
            self._state = 'WAITING'
            self._detail = 'Device node not present: {}'.format(self._device_path)
            self._next_retry = now + self._reconnect_initial
            return
        try:
            self._sdk = KromekSDK(self._library)
            self._device_id = self._sdk.start()
            self._sdk_version = self._sdk.version()
            self._state = 'INITIALIZING'
            self._detail = 'Waiting for valid SDK baseline'
            self._startup_deadline = now + self._startup_timeout
            self._next_sample = now  # baseline readings have 100 ms polling
            self.get_logger().info('SDK {} initialized; device_id={}'.format(
                self._sdk_version, self._device_id))
        except Exception as exc:
            self._fail(exc)

    def _baseline(self, now):
        sample = self._sdk.snapshot()
        if has_invalid_time(sample):
            if now >= self._startup_deadline:
                raise RuntimeError('No valid SDK startup time within timeout')
            return
        validate_snapshot(sample)
        if sample.real_ms < max(1, self._warmup_ms):
            if now >= self._startup_deadline:
                raise RuntimeError('No warmup baseline within startup timeout')
            return
        self._previous = sample
        self._state = 'ACQUIRING'
        self._detail = 'Publishing interval spectra'
        self._failures = 0
        self._next_sample = now + self._period
        self._invalid_since = None
        self.get_logger().info('Baseline accepted after {}ms real, {}ms live; '
                               'discarded {} initial counts'.format(
                                   sample.real_ms, sample.live_ms, sample.total))

    def _acquire(self, now):
        if not Path(self._device_path).exists():
            raise RuntimeError('USB device node disappeared')
        sample = self._sdk.snapshot()
        if has_invalid_time(sample):
            if self._invalid_since is None:
                self._invalid_since = now
            if now - self._invalid_since > self._invalid_timeout:
                raise RuntimeError('SDK timestamps invalid for {:.1f} s'.format(
                    self._invalid_timeout))
            if now - self._last_warning >= 1:
                self.get_logger().warn('Skipping invalid time (real={} live={})'.format(
                    sample.real_ms, sample.live_ms))
                self._last_warning = now
            self._next_sample = next_deadline(self._next_sample, now, self._period)
            return
        validate_snapshot(sample)
        interval = make_interval(self._previous, sample)
        self._previous = sample
        self._invalid_since = None
        # This is a HOST timestamp, not the time of every detected photon.
        end = self.get_clock().now()
        start = end - Duration(nanoseconds=interval.real_ms * 1000000)
        stamp = end.to_msg()

        m = RadiationMeasurement()
        m.header.stamp = stamp
        m.header.frame_id = self._frame
        m.interval_start = start.to_msg()
        m.interval_end = stamp
        m.device_id = self._device_id
        m.interval_counts = interval.total
        m.cumulative_counts = interval.cumulative_total
        m.interval_real_time_ms = interval.real_ms
        m.interval_live_time_ms = interval.live_ms
        m.cps_real = interval.cps_real
        m.cps_live = interval.cps_live
        m.live_fraction = interval.live_fraction

        s = RadiationSpectrum()
        s.header.stamp = stamp
        s.header.frame_id = self._frame
        s.device_id = self._device_id
        s.counts = list(interval.counts)
        self._measurement_pub.publish(m)
        self._spectrum_pub.publish(s)
        self._published_count += 1
        self._last_cps = interval.cps_real
        self._next_sample = next_deadline(self._next_sample, now, self._period)
        if self._published_count % 10 == 0:
            self.get_logger().info('CPS(real)={:.2f}, counts={}, duration={}ms; CPU(process)={:.1f}%'.format(
                interval.cps_real, interval.total, interval.real_ms, self._process_cpu_pct))

    def _publish_diagnostic(self, now):
        cpu = self._cpu_seconds()
        dt = now - self._cpu_last_time
        if dt > 0:
            self._process_cpu_pct = cpu_percentage(max(0.0, cpu - self._cpu_last_usage), dt)
        self._cpu_last_time = now
        self._cpu_last_usage = cpu
        r = resource.getrusage(resource.RUSAGE_SELF)
        status = DiagnosticStatus()
        status.name = 'kromek/sigma50'
        status.hardware_id = str(self._device_id) if self._device_id else 'SIGMA50 (disconnected)'
        status.level = (DiagnosticStatus.OK if self._state == 'ACQUIRING' else
                        DiagnosticStatus.WARN if self._state in ('WAITING', 'INITIALIZING') else
                        DiagnosticStatus.ERROR)
        status.message = '{}: {}'.format(self._state, self._detail)
        for k, v in (
            ('state', self._state), ('sdk_version', self._sdk_version),
            ('device_path', self._device_path), ('published_intervals', self._published_count),
            ('recovery_failures', self._failures),
            ('process_cpu_pct', '{:.1f}'.format(self._process_cpu_pct)),
            ('max_rss_kib', r.ru_maxrss),
            ('last_cps_real', self._last_cps if self._last_cps is not None else 'not measured'),
            ('time_basis', 'SDK cumulative real/live milliseconds; host ROS receipt stamps'),
        ):
            x = KeyValue()
            x.key, x.value = str(k), str(v)
            status.values.append(x)
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.status = [status]
        self._diagnostics.publish(msg)

    def _tick(self):
        now = time.monotonic()
        try:
            if self._state in ('WAITING', 'RECOVERING') and now >= self._next_retry:
                self._connect(now)
            elif self._state == 'INITIALIZING' and now >= self._next_sample:
                self._baseline(now)
            elif self._state == 'ACQUIRING' and now >= self._next_sample:
                self._acquire(now)
        except Exception as exc:
            self._fail(exc)
        if now >= self._next_diagnostic:
            self._publish_diagnostic(now)
            self._next_diagnostic = now + 1.0

    def destroy_node(self):
        self._close_sdk()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = Sigma50Node()
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
