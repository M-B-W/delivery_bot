
import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    AppendEnvironmentVariable,
    TimerAction
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    Command
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    use_sim_time = LaunchConfiguration('use_sim_time')

    world_file = os.path.expanduser(
        '~/butler_ws/src/butler_bot/worlds/restaurant.world'
    )

    rviz_config = PathJoinSubstitution([
        FindPackageShare('butler_bot'),
        'config',
        'butler_simulation.rviz'
    ])

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('gazebo_ros'),
                'launch',
                'gazebo.launch.py'
            ])
        ),
        launch_arguments={
            'world': world_file,
            'verbose': 'true'
        }.items()
    )

    turtlebot_model = PathJoinSubstitution([
        FindPackageShare('turtlebot3_gazebo'),
        'models',
        'turtlebot3_burger',
        'model.sdf'
    ])

    urdf_file = PathJoinSubstitution([
        FindPackageShare('turtlebot3_description'),
        'urdf',
        'turtlebot3_burger.urdf'
    ])

    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]),
        value_type=str
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time
        }]
    )

    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'burger',
            '-file', turtlebot_model,
            '-x', '-3.0',
            '-y', '-2.0',
            '-z', '0.01'
        ],
        output='screen'
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=[
            '-d',
            rviz_config
        ],
        parameters=[{
            'use_sim_time': use_sim_time
        }]
    )

    return LaunchDescription([

        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true'
        ),

        AppendEnvironmentVariable(
            name='GAZEBO_MODEL_PATH',
            value='/usr/share/gazebo-11/models'
        ),

        gazebo_launch,

        robot_state_publisher,

        TimerAction(
            period=4.0,
            actions=[spawn_robot]
        ),

        TimerAction(
            period=7.0,
            actions=[rviz]
        )

    ])
