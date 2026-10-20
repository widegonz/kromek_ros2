#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET=/etc/systemd/system/kromek-ros2.service
[[ "$ROOT" == /home/unitree/kromek_ros2 ]] || { echo "Template currently assumes /home/unitree/kromek_ros2; adapt it for other robots" >&2; exit 1; }
[[ -e "$ROOT/install/kromek_driver" && -e "$ROOT/install/kromek_interfaces" ]] || { echo 'Build ROS packages first' >&2; exit 1; }
[[ -e "$ROOT/vendor/dr_park/source/SpectrometerPackage/output/linux64/release/libSpectrometerDriver.so" ]] || { echo 'Build SDK first' >&2; exit 1; }
case "${1:-}" in
  --show) cat "$ROOT/systemd/kromek-ros2.service" ;;
  --install) sudo install -m 0644 "$ROOT/systemd/kromek-ros2.service" "$TARGET" && sudo systemctl daemon-reload && echo 'Installed but NOT enabled or started. Review then run: sudo systemctl enable --now kromek-ros2.service';;
  *) echo 'Usage: scripts/install_service.sh --show|--install  (never enables automatically)' >&2; exit 2;;
esac
