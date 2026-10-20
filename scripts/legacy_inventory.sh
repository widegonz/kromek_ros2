#!/usr/bin/env bash
# Read-only legacy inventory; DOES NOT delete/move/archive anything.
set -eo pipefail
printf '%s\n' '=== KROMEK LEGACY INVENTORY (READ ONLY) ==='
date -Is
for dir in "$HOME/kromek_stage1" "$HOME/kromek_stage2" "$HOME/kromek_stage3" "$HOME/kromek_stage4" "$HOME/kromek_ws" "$HOME/kromek_vendor" "$HOME/radiation_mapping_ws" "$HOME/Downloads/kromek"; do
  if [[ -e "$dir" ]]; then
    du -sh "$dir" 2>/dev/null || true
  fi
done
printf '%s\n' '=== LEGACY FILES IN HOME (depth 1) ==='
find "$HOME" -maxdepth 1 -type f \( -name 'kromek*.zip' -o -name '*stage*.zip' -o -name 'SDK_linux.zip' \) -print
printf '%s\n' '=== BACKEND SERVICES ==='
systemctl list-unit-files --type=service --no-pager 2>/dev/null | grep -Ei 'kromek|sigma50|radiation' || true
printf '%s\n' '=== ACTIVE SENSOR PROCESSES / OWNERS ==='
ps -eo pid,comm,args | grep -Ei '[s]igma50_node|[k]romek|[r]adiation_mapper' | head -25 || true
fuser -v /dev/kromek0 2>&1 || true
printf '%s\n' '=== SHELL / SERVICE REFERENCES TO OLD WORKSPACE ==='
grep -HnE 'kromek_stage|kromek_vendor|radiation_mapping_ws|kromek_ws' "$HOME/.bashrc" "$HOME/.profile" 2>/dev/null || true
# Broad service scan; failures if unreadable are expected for ordinary users.
grep -RInE 'kromek_stage|radiation_mapping_ws' /etc/systemd/system/*.service 2>/dev/null | head -35 || true
printf '%s\n' '=== IMPORTANT: Never remove /lib/modules/.../kromekusb.ko, /etc/udev/rules.d/*kromek*, CycloneDDS, or RADIANT here ==='
