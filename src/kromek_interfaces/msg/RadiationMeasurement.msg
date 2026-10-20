# A single interval of acquisition (not cumulative).
# header.stamp is the host read timestamp; times approximate the acquisition window.
std_msgs/Header header
builtin_interfaces/Time interval_start
builtin_interfaces/Time interval_end
uint32 device_id
uint32 interval_counts
uint32 cumulative_counts
uint32 interval_real_time_ms
uint32 interval_live_time_ms
float64 cps_real
float64 cps_live
float64 live_fraction
