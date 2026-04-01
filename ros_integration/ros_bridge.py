"""
Optional ROS2 bridge for future real robot extension.

This module is intentionally non-blocking: if rclpy is unavailable,
it silently runs in disabled mode so the simulation still works.
"""

from __future__ import annotations

import importlib


class ROSBridge:
    """Lightweight optional bridge for publishing simulation state."""

    def __init__(self, enabled=False):
        self.enabled = False
        self._node = None
        self._publisher = None

        if not enabled:
            return

        try:
            rclpy = importlib.import_module("rclpy")
            node_mod = importlib.import_module("rclpy.node")
            std_msgs_mod = importlib.import_module("std_msgs.msg")
        except Exception:
            return

        self._rclpy = rclpy
        self._String = std_msgs_mod.String
        self._Node = node_mod.Node

        try:
            rclpy.init(args=None)
            self._node = self._Node("robot_path_sim_bridge")
            self._publisher = self._node.create_publisher(self._String, "/sim/state", 10)
            self.enabled = True
        except Exception:
            self.enabled = False

    def publish_state(self, state_name, robot_pos, metrics):
        if not self.enabled:
            return

        msg = self._String()
        msg.data = (
            f"state={state_name};"
            f"x={robot_pos[0]:.3f};"
            f"y={robot_pos[1]:.3f};"
            f"nodes={metrics.get('nodes', 0)};"
            f"path_len={metrics.get('path_len', 0)}"
        )
        self._publisher.publish(msg)
        self._rclpy.spin_once(self._node, timeout_sec=0.0)

    def shutdown(self):
        if not self.enabled:
            return
        try:
            self._node.destroy_node()
            self._rclpy.shutdown()
        except Exception:
            pass
        self.enabled = False
