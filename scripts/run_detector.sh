#!/usr/bin/env bash
# Stage 4: inherit the working ROS 2 / CycloneDDS environment from the shell.
# For systemd, set up the same environment explicitly in the unit (not via ~/.bashrc).
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB="$ROOT/vendor/dr_park/source/SpectrometerPackage/output/linux64/release/libSpectrometerDriver.so"

[[ -f "$LIB" ]] || { echo "ERROR: SDK library missing: $LIB" >&2; exit 1; }
[[ -f "$ROOT/install/local_setup.bash" ]] || { echo "ERROR: Build this workspace first: ./scripts/build_ros.sh" >&2; exit 1; }

if [[ "${ROS_DISTRO:-}" != "foxy" ]]; then
  echo "ERROR: ROS 2 Foxy is not loaded in this terminal. Open a new SSH shell configured with ~/.bashrc." >&2
  exit 1
fi
if [[ "${RMW_IMPLEMENTATION:-}" != "rmw_cyclonedds_cpp" ]]; then
  echo "ERROR: Expected rmw_cyclonedds_cpp from the robot environment; current: ${RMW_IMPLEMENTATION:-unset}" >&2
  exit 1
fi
if [[ -z "${CYCLONEDDS_URI:-}" ]]; then
  echo "ERROR: CYCLONEDDS_URI is unset. Use the robot's working CycloneDDS configuration." >&2
  exit 1
fi

# Put THIS repository ahead of older workspaces and packages.
source "$ROOT/install/local_setup.bash"
for pkg in kromek_interfaces kromek_driver; do
  prefix="$(ros2 pkg prefix "$pkg")" || exit 1
  expected="$ROOT/install/$pkg"
  if [[ "$prefix" != "$expected" ]]; then
    echo "ERROR: $pkg resolves to $prefix, expected $expected" >&2
    exit 1
  fi
done

echo "Using ROS_DISTRO=$ROS_DISTRO"
echo "Using RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
echo "Using CYCLONEDDS_URI=$CYCLONEDDS_URI"
echo "Using kromek_driver from $ROOT"

exec ros2 launch kromek_driver detector.launch.py sdk_library:="$LIB" "$@"
