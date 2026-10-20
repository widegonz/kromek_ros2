# RC1 — consolidación Stage 4.1 (ROS 2 Foxy)

## Verified in previously uploaded logs (not yet hardware-tested as RC1)
- Stage 4 has recovered twice from unplug/replug.
- Native SDK reports version 16.3.9.24.
- During acquisition, logged process CPU ~4–6% (not a long-run guarantee).
- Stage 4 Park-vs-ROS comparison normalized rates: difference <1% in previous test.

## Changes in RC1
1. Monotonic phase-locked sampling deadlines; skip missed slots instead of drifting with callback completion time. SDK-reported interval duration remains source of truth for CPS. Host timestamps remain approximate.
2. Native SDK `ERROR_INVALID_DEVICE_ID=7` during STOP is recognized and reported as a **warning**, not silently ignored. Known unplug avoids STOP entirely but calls kr_Destruct. Other return codes raise after cleanup.
3. Read-only `legacy_inventory.sh`; update script protects vendor/, data/, and generated build artifacts. No automatic deletion.
4. Optional service template using the existing Go2 Foxy/CycloneDDS configuration. It is NOT enabled or started on install.
5. Tests for deadline scheduling and disconnected cleanup.

## Required acceptance before enabling service or cleanup
- Unit tests pass.
- Build is independent of RADIANT and old radiation_mapping_ws.
- Real SIGMA50 publishes measurements and 4096-channel spectra at desired cadence.
- Validate DDS connectivity; inspect /diagnostics (no stale zeros during loss).
- Five-minute rosbag of RC1; check interval_real_time_ms distribution (1000/1100 may persist due SDK granularity) and counts.
- Repeat unplug/replug with stationary robot; confirm last timestamp and cumulative reference reset.
- Optional service: install, verify a cold boot and reconnect, only then enable.
- Check legacy inventory and back up old data before retiring old versions. Never remove kernel driver/udev without separate audited replacement.

## Known limitations
- SDK reports elapsed times in discrete milliseconds that may be quantized by device/firmware. The host timer cannot guarantee 1000 ms SDK durations.
- Measurement stamps represent host completion estimates, not timestamps of individual gamma events. Spatial integration over robot trajectory is a future mapper task.
- Native SDK may block unexpectedly; Python cannot interrupt native calls safely from the same thread.
- The systemd service template assumes `/home/unitree` and a custom CycloneDDS workspace. Adapt these paths on another robot; not a generic one-command installer yet.
