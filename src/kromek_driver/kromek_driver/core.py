"""Pure-Python accumulated spectrum validation, independent of ROS and USB."""
from dataclasses import dataclass
from typing import Tuple

CHANNELS = 4096
# Taken from Dr. Park's linux_python_code: reject uint32-like startup values.
INVALID_TIME_THRESHOLD = 0xF0000000


@dataclass(frozen=True)
class Snapshot:
    counts: Tuple[int, ...]
    total: int
    real_ms: int
    live_ms: int


def has_invalid_time(sample: Snapshot) -> bool:
    """Known SDK startup sentinel/underflow: skip rather than publish."""
    return (sample.real_ms >= INVALID_TIME_THRESHOLD or
            sample.live_ms >= INVALID_TIME_THRESHOLD)


def validate_snapshot(sample: Snapshot) -> None:
    if len(sample.counts) != CHANNELS:
        raise ValueError('Expected {} channels, got {}'.format(CHANNELS, len(sample.counts)))
    if sample.total < 0 or any(x < 0 for x in sample.counts):
        raise ValueError('Negative cumulative counts')
    if sum(sample.counts) != sample.total:
        raise ValueError('SDK total differs from spectrum sum')
    if has_invalid_time(sample):
        raise ValueError('Invalid uint32-like SDK real/live time')
    if not (0 <= sample.live_ms <= sample.real_ms):
        raise ValueError('Invalid real/live times')


@dataclass(frozen=True)
class Interval:
    counts: Tuple[int, ...]
    total: int
    cumulative_total: int
    real_ms: int
    live_ms: int
    cps_real: float
    cps_live: float
    live_fraction: float


def make_interval(previous: Snapshot, current: Snapshot) -> Interval:
    validate_snapshot(previous)
    validate_snapshot(current)
    delta_real = current.real_ms - previous.real_ms
    delta_live = current.live_ms - previous.live_ms
    delta_total = current.total - previous.total
    if delta_real <= 0 or delta_live < 0 or delta_live > delta_real or delta_total < 0:
        raise ValueError('Cumulative counters/times reset or decreased')
    delta_channels = tuple(b - a for a, b in zip(previous.counts, current.counts))
    if any(c < 0 for c in delta_channels):
        raise ValueError('One or more cumulative channels decreased')
    if sum(delta_channels) != delta_total:
        raise ValueError('Interval spectrum differs from total count difference')
    return Interval(
        counts=delta_channels,
        total=delta_total,
        cumulative_total=current.total,
        real_ms=delta_real,
        live_ms=delta_live,
        cps_real=delta_total * 1000.0 / delta_real,
        cps_live=delta_total * 1000.0 / delta_live if delta_live > 0 else float('nan'),
        live_fraction=delta_live / delta_real,
    )
