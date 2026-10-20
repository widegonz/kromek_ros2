#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/vendor/dr_park/source/SpectrometerPackage"
[[ -f "$SRC/CMakeLists.txt" ]] || { echo "Run scripts/prepare_vendor.sh first" >&2; exit 1; }
[[ "$(id -u)" -ne 0 ]] || { echo "Do not compile as root" >&2; exit 1; }
for x in cmake c++ make file ldd gcc; do command -v "$x" >/dev/null || { echo "Missing $x" >&2; exit 1; }; done
[[ -f /usr/include/libudev.h ]] || { echo "Missing libudev-dev" >&2; exit 1; }
MULTIARCH="$(gcc -print-multiarch 2>/dev/null || true)"
cmake -S "$SRC" -B "$SRC/build" -DBUILD_EXAMPLE=OFF -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="/usr/lib/${MULTIARCH:-aarch64-linux-gnu}"
cmake --build "$SRC/build" --target SpectrometerDriver --parallel 2
LIB="$SRC/output/linux64/release/libSpectrometerDriver.so"
[[ -f "$LIB" ]] || { echo "Library missing: $LIB" >&2;exit 1; }
file "$LIB"
ldd "$LIB"
if ldd "$LIB" | grep -q 'not found'; then echo "Unresolved dependencies" >&2;exit 1;fi
sha256sum "$(readlink -f "$LIB")"
echo "KROMEK_SDK_LIB=$LIB"
echo 'Kernel module, udev permissions and old workspaces were not modified.'
