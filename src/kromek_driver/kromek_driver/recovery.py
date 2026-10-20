"""Small, hardware-independent backoff and rate sanity helpers."""


def retry_delay(failure_number, first=2.0, maximum=30.0):
    """Bounded exponential delay for nonnegative consecutive failure count."""
    if failure_number < 1 or first <= 0 or maximum < first:
        raise ValueError('Invalid retry configuration')
    return min(maximum, first * (2 ** min(20, failure_number - 1)))


def cpu_percentage(cpu_delta_s, wall_delta_s):
    """100% corresponds to one fully occupied logical core."""
    if wall_delta_s <= 0 or cpu_delta_s < 0:
        raise ValueError('Invalid CPU sampling times')
    return 100.0 * cpu_delta_s / wall_delta_s


def next_deadline(deadline, now, period):
    """Next tick on the existing monotonic grid, not `now + period`.

    Overruns skip missed slots instead of a catch-up acquisition burst.
    Real integration time is still read from SDK (not assumed = period).
    """
    if period <= 0:
        raise ValueError('Sampling period must be positive')
    if deadline > now:
        return deadline
    missed = int((now - deadline) // period) + 1
    return deadline + missed * period
