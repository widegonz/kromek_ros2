#!/usr/bin/env python3
"""Validate ROS 2 Foxy SIGMA50 rosbag2 data without importing ROS.

Reads the known v2 message schemas for kromek_interfaces/RadiationMeasurement
and RadiationSpectrum. Outputs one CSV per interval and one aggregated
4096-channel CSV. Python 3.8+ standard library only.
Usage: python3 validate_kromek_bag.py /path/to/bag_directory --output /path/to/output
"""
import argparse
import csv
import sqlite3
import struct
from pathlib import Path
from statistics import mean, stdev


def aligned(offset, alignment):
    # The first four bytes contain the CDR encapsulation header.
    return 4 + ((offset - 4 + alignment - 1) // alignment) * alignment


def unpack_common(blob):
    if blob[:4] != b'\x00\x01\x00\x00':
        raise ValueError('Expected little-endian CDR encoding')
    sec, nsec, length = struct.unpack_from('<iII', blob, 4)
    frame = blob[16:16 + length - 1].decode('utf8')
    return sec * 10**9 + nsec, frame, aligned(16 + length, 4)


def parse_measurement(blob):
    stamp, frame, offset = unpack_common(blob)
    start_s, start_ns, end_s, end_ns, device, counts, cumulative, real_ms, live_ms = struct.unpack_from('<iIiI5I', blob, offset)
    double_offset = aligned(offset + 36, 8)
    cps_real, cps_live, fraction = struct.unpack_from('<ddd', blob, double_offset)
    return dict(stamp_ns=stamp, frame_id=frame, start_ns=start_s * 10**9 + start_ns,
                end_ns=end_s * 10**9 + end_ns, device_id=device,
                counts=counts, cumulative_counts=cumulative, real_ms=real_ms,
                live_ms=live_ms, cps_real=cps_real, cps_live=cps_live,
                live_fraction=fraction)


def parse_spectrum(blob):
    stamp, frame, offset = unpack_common(blob)
    device = struct.unpack_from('<I', blob, offset)[0]
    channels = struct.unpack_from('<4096I', blob, offset + 4)
    return dict(stamp_ns=stamp, frame_id=frame, device_id=device, channels=channels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bag', type=Path, help='rosbag2 directory (containing .db3) or .db3 file')
    parser.add_argument('--output', type=Path, default=Path('kromek_checked'))
    args = parser.parse_args()
    db = args.bag if args.bag.suffix == '.db3' else next(iter(sorted(args.bag.glob('*.db3'))), None)
    if db is None or not db.exists():
        parser.error('No rosbag2 .db3 found')
    with sqlite3.connect(str(db)) as conn:
        topics = dict(conn.execute('SELECT id, name FROM topics'))
        measurements, spectra = {}, {}
        for topic_id, bag_ts, data in conn.execute('SELECT topic_id, timestamp, data FROM messages ORDER BY timestamp'):
            name = topics[topic_id]
            if name == '/kromek/measurement':
                parsed = parse_measurement(data)
                parsed['bag_timestamp_ns'] = bag_ts
                if parsed['stamp_ns'] in measurements:
                    raise ValueError('Duplicate measurement timestamp')
                measurements[parsed['stamp_ns']] = parsed
            elif name == '/kromek/spectrum':
                parsed = parse_spectrum(data)
                if parsed['stamp_ns'] in spectra:
                    raise ValueError('Duplicate spectrum timestamp')
                spectra[parsed['stamp_ns']] = parsed
    if not measurements or set(measurements) != set(spectra):
        raise ValueError('Missing measurement/spectrum pairs: {} vs {}'.format(len(measurements), len(spectra)))
    timestamps = sorted(measurements)
    totals = [0] * 4096
    rows = []
    for idx, stamp in enumerate(timestamps):
        m, s = measurements[stamp], spectra[stamp]
        if m['device_id'] != s['device_id'] or m['frame_id'] != s['frame_id']:
            raise ValueError('Device or TF frame mismatch at message {}'.format(idx))
        n = sum(s['channels'])
        if n != m['counts']:
            raise ValueError('Count mismatch at message {}'.format(idx))
        if m['real_ms'] <= 0 or not (0 < m['live_ms'] <= m['real_ms']):
            raise ValueError('Invalid duration at message {}'.format(idx))
        if abs(m['cps_real'] - 1000 * m['counts']/m['real_ms']) > 1e-7:
            raise ValueError('Real CPS mismatch at message {}'.format(idx))
        if abs(m['cps_live'] - 1000 * m['counts']/m['live_ms']) > 1e-7:
            raise ValueError('Live CPS mismatch at message {}'.format(idx))
        if abs(m['live_fraction'] - m['live_ms']/m['real_ms']) > 1e-9:
            raise ValueError('Live fraction mismatch at message {}'.format(idx))
        if m['end_ns'] != m['stamp_ns'] or (m['end_ns']-m['start_ns'])//10**6 != m['real_ms']:
            raise ValueError('Header / interval timing mismatch at message {}'.format(idx))
        if idx and m['cumulative_counts']-measurements[timestamps[idx-1]]['cumulative_counts'] != m['counts']:
            raise ValueError('Incorrect cumulative count difference at message {}'.format(idx))
        for i, count in enumerate(s['channels']):
            totals[i] += count
        rows.append(m)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    with (output/'measurements_checked.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (output/'spectrum_aggregated.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['channel', 'counts_total'])
        writer.writerows(enumerate(totals))
    count_total = sum(m['counts'] for m in rows)
    real_total = sum(m['real_ms'] for m in rows)/1000
    live_total = sum(m['live_ms'] for m in rows)/1000
    print('PASS: {} matched pairs; 4096 channels, {} counts.'.format(len(rows), count_total))
    print('Real rate: {:.6f} CPS; live rate: {:.6f} CPS'.format(count_total/real_total, count_total/live_total))
    print('Count mean {:.3f}, std {:.3f}; saturated/boundary channel 4095: {}'.format(mean(m['counts'] for m in rows), stdev(m['counts'] for m in rows), totals[4095]))
    print('Output:', output)


if __name__ == '__main__':
    main()
