# Delivery Bot --- ROS 2 Restaurant Delivery Robot

A ROS 2 restaurant delivery robot simulation using TurtleBot3 Burger,
Gazebo Classic, and Nav2. It demonstrates waypoint navigation and a
Python task manager for kitchen-to-table delivery workflows.

## Features

-   TurtleBot3 Burger simulation in a restaurant world
-   ROS 2 Humble and Nav2 navigation
-   YAML-based waypoint configuration
-   Python task manager using `rclpy` and `nav2_simple_commander`
-   Single-table and multi-table delivery workflows
-   Customer confirmation through `/butler/confirm`
-   Confirmation timeout handling
-   Cancellation requests through `/butler/cancel`

## Technology Stack

-   Ubuntu 22.04
-   ROS 2 Humble
-   Gazebo Classic
-   TurtleBot3 Burger
-   Nav2
-   Python and YAML

## Package Structure

``` text
butler_bot/
├── butler_bot/
│   ├── __init__.py
│   └── butler_task_manager.py
├── config/
│   ├── butler_simulation.rviz
│   ├── nav2_params.yaml
│   └── waypoints.yaml
├── launch/
│   ├── butler_simulation.launch.py
│   └── nav2.launch.py
├── maps/
│   ├── restaurant_map.pgm
│   └── restaurant_map.yaml
├── worlds/
│   └── restaurant.world
├── package.xml
├── setup.py
└── README.md
```

## Build

Install ROS 2 Humble and the required TurtleBot3, Gazebo, and Nav2
packages for Ubuntu 22.04.

``` bash
cd ~/butler_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Set the TurtleBot3 model:

``` bash
export TURTLEBOT3_MODEL=burger
```

## Run the Simulation

Run each command in a separate terminal.

### Terminal 1 --- Gazebo

``` bash
cd ~/butler_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch butler_bot butler_simulation.launch.py
```

### Terminal 2 --- Nav2

``` bash
cd ~/butler_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch butler_bot nav2.launch.py use_sim_time:=True use_composition:=False autostart:=True
```

### Terminal 3 --- Verify navigation

``` bash
source /opt/ros/humble/setup.bash
ros2 action list | grep navigate
```

Start the task manager only after Nav2 is active.

## Run the Task Manager

Example: normal delivery to Table 1.

``` bash
cd ~/butler_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run butler_bot butler_manager --ros-args -p scenario:=1 -p "tables:=['table1']"
```

## Scenarios

The task manager accepts scenario IDs 1--7.

  Scenario   Workflow
  ---------- ----------------------------------------------
  1          Normal delivery: kitchen → table(s) → home
  2          Confirmation at kitchen and delivery table
  3          Confirmation timeout and recovery
  4          Cancellation request during navigation
  5          Multi-table delivery
  6          Skip a table after confirmation timeout
  7          Skip/cancel a specific table before its turn

Example: multi-table delivery.

``` bash
ros2 run butler_bot butler_manager --ros-args -p scenario:=5 -p "tables:=['table1','table2','table3']"
```

Example: confirmation workflow.

``` bash
ros2 run butler_bot butler_manager --ros-args -p scenario:=2 -p "tables:=['table1']" -p confirmation_timeout:=30.0
```

## Confirmation Commands

Publish these from another terminal after the manager displays the
corresponding confirmation prompt.

``` bash
source /opt/ros/humble/setup.bash

# Confirm kitchen
ros2 topic pub --once /butler/confirm std_msgs/msg/String "{data: 'kitchen'}"

# Confirm Table 1
ros2 topic pub --once /butler/confirm std_msgs/msg/String "{data: 'table1'}"

# Confirm Table 2
ros2 topic pub --once /butler/confirm std_msgs/msg/String "{data: 'table2'}"

# Confirm Table 3
ros2 topic pub --once /butler/confirm std_msgs/msg/String "{data: 'table3'}"
```

## Cancellation Commands

Cancel the current task:

``` bash
ros2 topic pub --once /butler/cancel std_msgs/msg/String "{data: 'all'}"
```

Request a specific table to be skipped/cancelled:

``` bash
ros2 topic pub --once /butler/cancel std_msgs/msg/String "{data: 'table2'}"
```

For Scenario 7, send the table-specific request before the robot begins
navigating to that table. The current implementation should not be
assumed to cancel a table goal that is already active.

## Waypoints

Waypoint positions are configured in:

``` text
config/waypoints.yaml
```

Configured waypoint names:

-   `home`
-   `kitchen`
-   `table1`
-   `table2`
-   `table3`

Verify waypoint coordinates and localization in the map before running
delivery tests.

## Useful ROS 2 Checks

``` bash
# List navigation actions
ros2 action list

# Check confirmation topic
ros2 topic info /butler/confirm

# Check cancellation topic
ros2 topic info /butler/cancel

# View AMCL pose
ros2 topic echo /amcl_pose
```

## Validation Status

-   Scenario 1 (normal single-table delivery) has been run successfully
    in the development environment.
-   Other scenarios need individual testing before they can be marked as
    passed.
-   Verify waypoint positions, localization, and recovery behavior in
    your own simulation before recording results.

## Future Improvements

-   Improve cancellation handling during an active navigation goal
-   Add automated tests for all scenarios
-   Improve waypoint calibration and localization accuracy
-   Add clearer delivery status reporting and logs

## Author

**Bharathwaj M**

## License

Add a license before redistributing or reusing this project.
