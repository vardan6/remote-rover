from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    config_path = LaunchConfiguration("config_path")
    return LaunchDescription([
        DeclareLaunchArgument(
            "config_path",
            default_value="config/rover_sim_next.example.yaml",
            description="Path to the rover-sim-next config file.",
        ),
        LogInfo(msg=["rover-sim-next scaffold launch. config_path=", config_path]),
    ])
