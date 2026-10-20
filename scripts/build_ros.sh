#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f /opt/ros/foxy/setup.bash ]] || { echo "ROS 2 Foxy is not installed" >&2; exit 1; }
# Explicitly avoid inheriting old underlays. This subprocess does NOT edit ~/.bashrc.
exec env -i HOME="$HOME" USER="${USER:-unitree}" LOGNAME="${LOGNAME:-unitree}" \
 PATH="/usr/local/bin:/usr/bin:/bin" TERM="${TERM:-xterm}" \
 ROOT="$ROOT" bash --noprofile --norc -c '
    set -Eeo pipefail
    source /opt/ros/foxy/setup.bash
    cd "$ROOT"
    colcon list
    colcon build --symlink-install --packages-up-to kromek_driver
    source install/local_setup.bash
    ros2 pkg prefix kromek_interfaces
    ros2 pkg prefix kromek_driver
    ros2 interface show kromek_interfaces/msg/RadiationMeasurement
'
