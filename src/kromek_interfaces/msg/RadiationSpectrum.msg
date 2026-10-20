# 4096 per-channel interval counts, not accumulated spectrum.
# Matching the Measurement header stamp links each pair of messages.
std_msgs/Header header
uint32 device_id
uint32[4096] counts
