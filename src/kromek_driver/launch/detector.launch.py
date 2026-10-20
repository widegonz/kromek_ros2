"""RADIANT compatible ROS 2 Foxy Kromek-only launch; no dashboard."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = {
        'sdk_library': '/opt/kromek/lib/libSpectrometerDriver.so',
        'device_path': '/dev/kromek0',
        'sample_period_s': '1.0',
        'startup_timeout_s': '5.0',
        'warmup_real_s': '1.0',
        'invalid_timeout_s': '5.0',
        'reconnect_initial_s': '2.0',
        'reconnect_max_s': '30.0',
        'frame_id': 'kromek_link',
    }
    return LaunchDescription(
        [DeclareLaunchArgument(k, default_value=v) for k, v in args.items()] + [
            Node(package='kromek_driver', executable='sigma50_node',
                 namespace='kromek', output='screen',
                 parameters=[{k: LaunchConfiguration(k) for k in args}]),
        ])
