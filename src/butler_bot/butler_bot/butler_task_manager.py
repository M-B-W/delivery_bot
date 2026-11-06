
#!/usr/bin/env python3

import math
import os
import time

import yaml
import rclpy

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from std_msgs.msg import String


class ButlerTaskManager(BasicNavigator):

    VALID_TABLES = ('table1', 'table2', 'table3')

    def __init__(self):
        super().__init__(node_name='butler_task_manager')

        self.declare_parameter('scenario', 1)
        self.declare_parameter('tables', ['table1'])
        self.declare_parameter('confirmation_timeout', 15.0)

        self.scenario = int(self.get_parameter('scenario').value)
        self.tables = list(self.get_parameter('tables').value)
        self.timeout = float(
            self.get_parameter('confirmation_timeout').value
        )

        if self.scenario not in range(1, 8):
            raise ValueError('Scenario must be between 1 and 7')

        if not self.tables:
            raise ValueError('At least one table order is required')

        for table in self.tables:
            if table not in self.VALID_TABLES:
                raise ValueError(f'Invalid table: {table}')

        package_share = get_package_share_directory('butler_bot')
        waypoint_file = os.path.join(
            package_share, 'config', 'waypoints.yaml'
        )

        with open(waypoint_file, encoding='utf-8') as file:
            config = yaml.safe_load(file)

        self.waypoints = config['waypoints']

        for name in ('home', 'kitchen', *self.VALID_TABLES):
            if name not in self.waypoints:
                raise ValueError(f'Missing waypoint: {name}')

        self.confirmation = None
        self.cancel_request = None
        self.cancelled_tables = set()

        self.create_subscription(
            String,
            '/butler/confirm',
            self.confirm_callback,
            10
        )

        self.create_subscription(
            String,
            '/butler/cancel',
            self.cancel_callback,
            10
        )

        self.get_logger().info(
            f'Butler manager started. Scenario: {self.scenario}'
        )
        self.get_logger().info(f'Orders: {self.tables}')
        self.get_logger().info(
            f'Loaded waypoints: {list(self.waypoints.keys())}'
        )

    # --------------------------------------------------
    # User input callbacks
    # --------------------------------------------------

    def confirm_callback(self, msg):
        self.confirmation = msg.data.strip().lower()

    def cancel_callback(self, msg):
        request = msg.data.strip().lower()

        if request in ('all', 'cancel', 'stop'):
            self.cancel_request = 'all'
        elif request in self.VALID_TABLES:
            self.cancelled_tables.add(request)
            self.get_logger().warn(
                f'Cancellation registered for {request}'
            )
        else:
            self.get_logger().warn(
                f'Unknown cancellation request: {request}'
            )

    # --------------------------------------------------
    # Waypoint handling
    # --------------------------------------------------

    def create_goal(self, destination):
        waypoint = self.waypoints[destination]

        goal = PoseStamped()
        goal.header.frame_id = 'map'
        goal.header.stamp = self.get_clock().now().to_msg()

        goal.pose.position.x = float(waypoint['x'])
        goal.pose.position.y = float(waypoint['y'])

        yaw = float(waypoint['yaw'])
        goal.pose.orientation.z = math.sin(yaw / 2.0)
        goal.pose.orientation.w = math.cos(yaw / 2.0)

        return goal

    # --------------------------------------------------
    # Navigation
    # Returns: reached, failed, cancelled
    # --------------------------------------------------

    def navigate(self, destination):
        self.get_logger().info(
            f'Navigating to {destination}'
        )

        self.goToPose(self.create_goal(destination))

        while not self.isTaskComplete():
            rclpy.spin_once(self, timeout_sec=0.1)

            if self.scenario == 4 and self.cancel_request == 'all':
                self.get_logger().warn(
                    f'Cancellation during travel to {destination}'
                )
                self.cancelTask()

                while not self.isTaskComplete():
                    rclpy.spin_once(self, timeout_sec=0.1)

                self.cancel_request = None
                return 'cancelled'

        result = self.getResult()

        if result == TaskResult.SUCCEEDED:
            self.get_logger().info(
                f'Successfully reached {destination}'
            )
            return 'reached'

        self.get_logger().error(
            f'Navigation failed at {destination}'
        )
        return 'failed'

    # --------------------------------------------------
    # Customer confirmation
    # --------------------------------------------------

    def wait_confirmation(self, stage):
        self.confirmation = None

        self.get_logger().info(
            f'Waiting for confirmation: {stage}'
        )

        deadline = time.monotonic() + self.timeout

        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

            if self.confirmation == stage:
                self.get_logger().info(
                    f'Confirmation received: {stage}'
                )
                return True

        self.get_logger().warn(
            f'Confirmation timeout: {stage}'
        )
        return False

    # --------------------------------------------------
    # Recovery helpers
    # --------------------------------------------------

    def return_home(self):
        result = self.navigate('home')
        if result != 'reached':
            self.get_logger().error('Could not return Home')
            return False
        return True

    def kitchen_then_home(self):
        result = self.navigate('kitchen')

        if result != 'reached':
            self.get_logger().error(
                'Could not reach Kitchen during recovery'
            )
            return False

        return self.return_home()

    # --------------------------------------------------
    # Scenario 1
    # Normal delivery
    # --------------------------------------------------

    def scenario_1(self):
        self.get_logger().info('SCENARIO 1: Normal delivery')

        if self.navigate('kitchen') != 'reached':
            return False

        for table in self.tables:
            if self.navigate(table) != 'reached':
                self.get_logger().error(
                    f'Delivery failed: {table}'
                )
                return False

        return self.return_home()

    # --------------------------------------------------
    # Scenario 2
    # Confirmation at Kitchen and tables.
    # Timeout: return Home.
    # --------------------------------------------------

    def scenario_2(self):
        self.get_logger().info(
            'SCENARIO 2: Confirmation with Home recovery'
        )

        if self.navigate('kitchen') != 'reached':
            return False

        if not self.wait_confirmation('kitchen'):
            return self.return_home()

        for table in self.tables:
            if self.navigate(table) != 'reached':
                return self.return_home()

            if not self.wait_confirmation(table):
                return self.return_home()

        return self.return_home()

    # --------------------------------------------------
    # Scenario 3
    # Kitchen timeout: Home.
    # Table timeout: Kitchen then Home.
    # --------------------------------------------------

    def scenario_3(self):
        self.get_logger().info(
            'SCENARIO 3: Stage-specific timeout recovery'
        )

        if self.navigate('kitchen') != 'reached':
            return False

        if not self.wait_confirmation('kitchen'):
            return self.return_home()

        for table in self.tables:
            if self.navigate(table) != 'reached':
                return self.kitchen_then_home()

            if not self.wait_confirmation(table):
                return self.kitchen_then_home()

        return self.return_home()

    # --------------------------------------------------
    # Scenario 4
    # Cancellation while travelling to Kitchen:
    # Home.
    #
    # Cancellation while travelling to a table:
    # Kitchen then Home.
    # --------------------------------------------------

    def scenario_4(self):
        self.get_logger().info(
            'SCENARIO 4: Navigation cancellation recovery'
        )

        result = self.navigate('kitchen')

        if result == 'cancelled':
            return self.return_home()

        if result != 'reached':
            return self.return_home()

        for table in self.tables:
            result = self.navigate(table)

            if result == 'cancelled':
                return self.kitchen_then_home()

            if result != 'reached':
                return self.kitchen_then_home()

        return self.return_home()

    # --------------------------------------------------
    # Scenario 5
    # Multiple orders.
    # --------------------------------------------------

    def scenario_5(self):
        self.get_logger().info(
            'SCENARIO 5: Multiple table deliveries'
        )

        if self.navigate('kitchen') != 'reached':
            return False

        for table in self.tables:
            if self.navigate(table) != 'reached':
                self.get_logger().error(
                    f'Unable to deliver to {table}'
                )
                return False

        return self.return_home()

    # --------------------------------------------------
    # Scenario 6
    # Skip unattended tables and continue.
    # After last table: Kitchen then Home.
    # --------------------------------------------------

    def scenario_6(self):
        self.get_logger().info(
            'SCENARIO 6: Unattended table handling'
        )

        if self.navigate('kitchen') != 'reached':
            return False

        if not self.wait_confirmation('kitchen'):
            return self.return_home()

        for table in self.tables:
            if self.navigate(table) != 'reached':
                self.get_logger().warn(
                    f'Skipping unreachable table: {table}'
                )
                continue

            if not self.wait_confirmation(table):
                self.get_logger().warn(
                    f'Unattended order skipped: {table}'
                )
                continue

            self.get_logger().info(
                f'Delivery confirmed: {table}'
            )

        return self.kitchen_then_home()

    # --------------------------------------------------
    # Scenario 7
    # Skip cancelled table orders.
    # After remaining orders: Kitchen then Home.
    # --------------------------------------------------

    def scenario_7(self):
        self.get_logger().info(
            'SCENARIO 7: Cancelled table order handling'
        )

        if self.navigate('kitchen') != 'reached':
            return False

        if not self.wait_confirmation('kitchen'):
            return self.return_home()

        for table in self.tables:

            if table in self.cancelled_tables:
                self.get_logger().warn(
                    f'Skipping cancelled order: {table}'
                )
                continue

            if self.navigate(table) != 'reached':
                self.get_logger().warn(
                    f'Skipping failed table: {table}'
                )
                continue

            if table in self.cancelled_tables:
                self.get_logger().warn(
                    f'Order cancelled at {table}'
                )
                continue

            if not self.wait_confirmation(table):
                self.get_logger().warn(
                    f'No confirmation at {table}; skipping'
                )

        return self.kitchen_then_home()

    # --------------------------------------------------
    # Mission dispatcher
    # --------------------------------------------------

    def run_task(self):
        self.get_logger().info('Waiting for Nav2...')

        self.waitUntilNav2Active()

        scenarios = {
            1: self.scenario_1,
            2: self.scenario_2,
            3: self.scenario_3,
            4: self.scenario_4,
            5: self.scenario_5,
            6: self.scenario_6,
            7: self.scenario_7,
        }

        success = scenarios[self.scenario]()

        if success:
            self.get_logger().info(
                f'SCENARIO {self.scenario} COMPLETED'
            )
        else:
            self.get_logger().error(
                f'SCENARIO {self.scenario} FINISHED WITH FAILURE'
            )


def main(args=None):
    rclpy.init(args=args)

    node = ButlerTaskManager()

    try:
        node.run_task()

    except KeyboardInterrupt:
        node.get_logger().warn('Mission interrupted')

        try:
            node.cancelTask()
        except Exception:
            pass

    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
