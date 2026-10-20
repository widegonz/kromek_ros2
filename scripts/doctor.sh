#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo '# Kromek Stage4 doctor (read-only)'
date -Is;uname -a
cat /etc/os-release | grep -E '^(NAME|VERSION)=' || true
echo 'USB:';lsusb -d 04d8:0023 || true
echo 'Device:';stat -c '%n %A %U:%G' /dev/kromek0 || true
echo 'Kernel module:';modinfo kromekusb 2>/dev/null | grep -E '^(filename|vermagic):' || true
echo 'Processes using USB device:';fuser -v /dev/kromek0 2>&1 || true
echo 'SDK library:';find "$ROOT/vendor/dr_park" -name 'libSpectrometerDriver.so*' -type f -o -name 'libSpectrometerDriver.so' 2>/dev/null | head -10
echo 'Old services:';systemctl is-active sigma50-dashboard.service 2>/dev/null || true
echo 'Workspace references:';env | grep -E '^(AMENT_PREFIX_PATH|CMAKE_PREFIX_PATH|ROS_DISTRO|RMW_IMPLEMENTATION)=' || true
