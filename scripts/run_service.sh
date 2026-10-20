#!/usr/bin/env bash
# For systemd, no reliance on interactive .bashrc. Match the proven RealSense DDS environment.
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB="$ROOT/vendor/dr_park/source/SpectrometerPackage/output/linux64/release/libSpectrometerDriver.so"
[[ -f "$LIB" ]] || { echo "Missing vendor SDK: $LIB" >&2; exit 1; }
[[ -f "$ROOT/install/local_setup.bash" ]] || { echo "Workspace not built: $ROOT/install" >&2; exit 1; }
source /opt/ros/foxy/setup.bash
source /home/unitree/cyclonedds_ws/install/setup.bash
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=/home/unitree/cyclonedds_ws/cyclonedds.xml
source "$ROOT/install/local_setup.bash"
for pkg in kromek_driver kromek_interfaces; do
  prefix="$(ros2 pkg prefix "$pkg")" || exit 1
  [[ "$prefix" == "$ROOT/install/$pkg" ]] || { echo "Wrong $pkg prefix: $prefix" >&2; exit 1; }
done
exec ros2 launch kromek_driver detector.launch.py sdk_library:="$LIB" "$@"
