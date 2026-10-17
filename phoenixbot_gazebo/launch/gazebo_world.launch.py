# Copyright 2019 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Launch Phoenixbot in Gazebo Harmonic with ROS 2 Jazzy bridges."""

import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    gazebo_package = 'phoenixbot_gazebo'
    description_package = 'phoenixbot_description'

    gazebo_share = get_package_share_directory(gazebo_package)
    description_share = get_package_share_directory(description_package)
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')

    world = PathJoinSubstitution([
        gazebo_share,
        'worlds',
        LaunchConfiguration('world'),
    ])
    xacro_file = os.path.join(
        description_share, 'urdf', 'groundbot', 'phoenixbot.xacro')
    bridge_config = os.path.join(gazebo_share, 'config', 'bridge.yaml')

    robot_description = xacro.process_file(xacro_file).toxml()
    use_sim_time = LaunchConfiguration('use_sim_time')

    # Gazebo resolves model:// URIs from this path. Include the package share
    # directories so meshes referenced by package:// are also discoverable.
    existing_resource_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    resource_paths = [
        os.path.join(gazebo_share, 'models'),
        gazebo_share,
        description_share,
        # URDF package:// meshes are converted to model://<package>/... by
        # ros_gz_sim, so Gazebo must search the parent share directory.
        os.path.dirname(description_share),
    ]
    if existing_resource_path:
        resource_paths.insert(0, existing_resource_path)

    start_gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r ', world]}.items(),
        condition=UnlessCondition(LaunchConfiguration('headless')),
    )
    start_gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-s -r ', world]}.items(),
        condition=IfCondition(LaunchConfiguration('headless')),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='phoenixbot_bridge',
        parameters=[{
            'config_file': bridge_config,
            'expand_gz_topic_names': True,
            'use_sim_time': use_sim_time,
        }],
        output='screen',
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
        output='screen',
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_phoenixbot',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'phoenixbot',
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', LaunchConfiguration('z'),
            '-Y', LaunchConfiguration('yaw'),
        ],
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(gazebo_share, 'config', 'rviz', 'config.rviz')],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(LaunchConfiguration('rviz')),
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world', default_value='farm_triple_row.world',
            description='World file installed in phoenixbot_gazebo/worlds'),
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use the Gazebo simulation clock'),
        DeclareLaunchArgument(
            'headless', default_value='false',
            description='Run Gazebo server without its GUI'),
        DeclareLaunchArgument('x', default_value='7.03', description='Initial X position'),
        DeclareLaunchArgument('y', default_value='-1.40', description='Initial Y position'),
        DeclareLaunchArgument('z', default_value='0.0', description='Initial Z position'),
        DeclareLaunchArgument('yaw', default_value='-3.04', description='Initial yaw in radians'),
        DeclareLaunchArgument(
            'rviz', default_value='true', description='Launch RViz2'),
        SetEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH', os.pathsep.join(resource_paths)),
        start_gazebo_gui,
        start_gazebo_headless,
        bridge,
        robot_state_publisher,
        spawn_robot,
        rviz,
    ])
