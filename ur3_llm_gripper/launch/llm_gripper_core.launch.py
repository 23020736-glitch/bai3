"""Gazebo (UR3e + gripper + table + cubes + camera) + MoveIt 2 + perception + skill_executor."""

import os
import tempfile

import yaml
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ur3_llm_gripper import sdf_models as M
from ur3_llm_gripper.description import make_wrapper
from ur3_llm_gripper.layout import initial_layout


def _spawn(name, xml, tmp, x, y, z, rpy=(0, 0, 0)):
    path = os.path.join(tmp, name + ".sdf")
    with open(path, "w") as f:
        f.write(xml)

    r, p, yw = rpy

    return Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        output="screen",
        arguments=[
            "-file", path,
            "-entity", name,
            "-x", str(x),
            "-y", str(y),
            "-z", str(z),
            "-R", str(r),
            "-P", str(p),
            "-Y", str(yw),
        ],
    )


def _scene():
    with open(
        os.path.join(
            share("ur3_llm_gripper"),
            "config",
            "scene.yaml",
        )
    ) as f:
        return yaml.safe_load(f)


def spawn_table(context):
    sc = _scene()
    tmp = tempfile.mkdtemp(prefix="ur3_scene_")

    return [
        _spawn(
            "table",
            M.table_sdf(sc["table_top_z"]),
            tmp,
            0,
            0,
            0,
        )
    ]


def spawn_items(context):
    sc = _scene()

    top = sc["table_top_z"]
    cs = sc["cube_size"]

    scenario = LaunchConfiguration("scenario").perform(context)
    seed = LaunchConfiguration("seed").perform(context)

    layout = initial_layout(
        scenario,
        sc,
        int(seed) if seed else None,
    )

    tmp = tempfile.mkdtemp(prefix="ur3_scene_")
    nodes = []

    # Spawn zones
    for n, (x, y) in {
        **sc["zones"],
        **sc["temp_positions"],
    }.items():

        nodes.append(
            _spawn(
                n,
                M.patch_sdf(
                    n,
                    M.PATCH_RGB.get(n, M.TEMP_RGB),
                    sc["zone_size"],
                ),
                tmp,
                x,
                y,
                top + 0.001,
            )
        )

    # Spawn cubes
    for n, (x, y) in layout.items():

        color = n.split("_")[0]

        nodes.append(
            _spawn(
                n,
                M.cube_sdf(
                    n,
                    cs,
                    M.RGB[color],
                ),
                tmp,
                x,
                y,
                top + cs / 2 + 0.002,
            )
        )

    # Spawn camera
    c = sc["camera"]

    nodes.append(
        _spawn(
            "overhead_camera",
            M.camera_sdf(c),
            tmp,
            c["x"],
            c["y"],
            c["z"],
            (
                c["roll"],
                c["pitch"],
                c["yaw"],
            ),
        )
    )

    return nodes


def generate_launch_description():

    pkg = share("ur3_llm_gripper")

    # ---------------------------------------------------------
    # UR3e + custom gripper description
    # ---------------------------------------------------------

    ur_xacro = os.path.join(
        share("ur_description"),
        "urdf",
        "ur.urdf.xacro",
    )

    wrapper = os.path.join(
        tempfile.mkdtemp(prefix="ur3_gripper_desc_"),
        "ur3_gripper.urdf.xacro",
    )

    with open(ur_xacro) as f, open(wrapper, "w") as g:
        g.write(
            make_wrapper(
                f.read(),
                os.path.join(
                    pkg,
                    "urdf",
                    "gripper.xacro",
                ),
            )
        )

    ur_type = LaunchConfiguration("ur_type")

    # ---------------------------------------------------------
    # Gazebo + UR3e
    #
    # LinkAttacher được load trực tiếp vào Gazebo server.
    # ---------------------------------------------------------

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                share("ur_simulation_gazebo"),
                "launch",
                "ur_sim_control.launch.py",
            )
        ),
        launch_arguments={
            "ur_type": ur_type,
            "launch_rviz": "false",
            "description_file": wrapper,
            "runtime_config_package": "ur3_llm_gripper",
            "controllers_file": os.path.join(
                pkg,
                "config",
                "ur3_controllers.yaml",
            ),
            "gazebo_gui": "true",
            "world": os.path.join(
                pkg,
                "worlds",
                "llm_gripper.world",
            ),
        }.items(),
    )

    # ---------------------------------------------------------
    # LinkAttacher plugin
    #
    # Plugin sẽ được nạp vào Gazebo server bằng
    # GAZEBO_PLUGIN_PATH + -s.
    # ---------------------------------------------------------

    link_attacher_plugin = ExecuteProcess(
        cmd=[
            "bash",
            "-c",
            (
                "export GAZEBO_PLUGIN_PATH="
                + os.path.expanduser(
                    "~/ws3/install/ros2_linkattacher/lib"
                )
                + ":$GAZEBO_PLUGIN_PATH; "
                "echo '>>> LinkAttacher plugin path:' "
                "$GAZEBO_PLUGIN_PATH"
            ),
        ],
        output="screen",
    )

    # ---------------------------------------------------------
    # MoveIt 2
    # ---------------------------------------------------------

    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                share("ur_moveit_config"),
                "launch",
                "ur_moveit.launch.py",
            )
        ),
        launch_arguments={
            "ur_type": ur_type,
            "use_sim_time": "true",
            "launch_rviz": "true",
            "description_file": wrapper,
            "trajectory_execution.allowed_start_tolerance": "0.05",
        }.items(),
    )

    # ---------------------------------------------------------
    # Delete default Gazebo ground
    # ---------------------------------------------------------

    del_ground = ExecuteProcess(
        cmd=[
            "ros2",
            "service",
            "call",
            "/delete_entity",
            "gazebo_msgs/srv/DeleteEntity",
            "{name: 'ground_plane'}",
        ],
        output="screen",
    )

    # ---------------------------------------------------------
    # Gripper controller
    # ---------------------------------------------------------

    gripper_ctrl = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=[
            "gripper_controller",
            "-c",
            "/controller_manager",
        ],
    )

    # ---------------------------------------------------------
    # Perception
    # ---------------------------------------------------------

    perception = Node(
        package="ur3_llm_gripper",
        executable="perception_node",
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
            }
        ],
    )

    # ---------------------------------------------------------
    # Skill executor
    # ---------------------------------------------------------

    executor = Node(
        package="ur3_llm_gripper",
        executable="skill_executor",
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
            }
        ],
    )

    # ---------------------------------------------------------
    # Launch
    # ---------------------------------------------------------

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "ur_type",
                default_value="ur3e",
            ),

            DeclareLaunchArgument(
                "scenario",
                default_value="random",
            ),

            DeclareLaunchArgument(
                "seed",
                default_value="",
            ),

            # Load environment variable for LinkAttacher
            link_attacher_plugin,

            # Start Gazebo + UR3e
            sim,

            # Delete ground
            TimerAction(
                period=8.0,
                actions=[
                    del_ground
                ],
            ),

            # Table
            TimerAction(
                period=9.0,
                actions=[
                    OpaqueFunction(
                        function=spawn_table
                    )
                ],
            ),

            # Cubes + zones + camera
            TimerAction(
                period=11.0,
                actions=[
                    OpaqueFunction(
                        function=spawn_items
                    )
                ],
            ),

            # Gripper controller
            TimerAction(
                period=15.0,
                actions=[
                    gripper_ctrl
                ],
            ),

            # MoveIt
            TimerAction(
                period=17.0,
                actions=[
                    moveit
                ],
            ),

            # Camera perception
            TimerAction(
                period=26.0,
                actions=[
                    perception
                ],
            ),

            # Skill executor
            TimerAction(
                period=28.0,
                actions=[
                    executor
                ],
            ),
        ]
    )
