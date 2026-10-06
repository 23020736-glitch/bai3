import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
    ExecuteProcess,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():

    scenario = LaunchConfiguration("scenario")

    # ==========================================================
    # LAUNCH GỐC CỦA BÀI:
    # GIỮ NGUYÊN overhead_camera + 3 cube + 3 zone + temp...
    # ==========================================================
    core = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                os.path.expanduser("~"),
                "ws3/src/ur3_llm_gripper/launch/llm_gripper_core.launch.py",
            )
        ),
        launch_arguments={
            "scenario": scenario,
        }.items(),
    )

    pkg = os.path.join(
        os.path.expanduser("~"),
        "ws3/src/ur3_llm_gripper",
    )

    # ==========================================================
    # CHỈ THÊM 2 CUBE MỚI
    # KHÔNG THÊM/XÓA CAMERA
    # ==========================================================
    return LaunchDescription([
        DeclareLaunchArgument(
            "scenario",
            default_value="blocked",
        ),
        core,
    ])
