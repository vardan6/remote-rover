#!/usr/bin/env python3
from __future__ import annotations

import json

import rclpy
from rclpy.node import Node

from rover_sim_next.config import load_runtime_config
from rover_sim_next.runtime import resolve_runtime_summary


class RoverSimRuntimeNode(Node):
    def __init__(self) -> None:
        super().__init__("rover_sim_runtime")
        self.declare_parameter("config_path", "")
        self.declare_parameter("world_path", "")
        self.declare_parameter("spawn_x", 0.0)
        self.declare_parameter("spawn_y", 0.0)
        self.declare_parameter("spawn_z", 0.35)
        self.declare_parameter("spawn_yaw", 0.0)

        config_path = str(self.get_parameter("config_path").value).strip()
        world_path = str(self.get_parameter("world_path").value).strip()
        spawn_x = self.get_parameter("spawn_x").value
        spawn_y = self.get_parameter("spawn_y").value
        spawn_z = self.get_parameter("spawn_z").value
        spawn_yaw = self.get_parameter("spawn_yaw").value

        cfg, resolved_config = load_runtime_config(config_path)
        summary = resolve_runtime_summary(
            cfg,
            resolved_config,
            {
                "world_path": world_path,
                "spawn_x": spawn_x,
                "spawn_y": spawn_y,
                "spawn_z": spawn_z,
                "spawn_yaw": spawn_yaw,
            },
        )
        self._summary = summary

        self.get_logger().info("rover-sim-next runtime node started")
        self.get_logger().info(json.dumps(summary, indent=2))
        self.create_timer(15.0, self._heartbeat)

    def _heartbeat(self) -> None:
        self.get_logger().debug(
            f"runtime alive backend={self._summary['backend']} world={self._summary['world_path']}"
        )


def main() -> None:
    rclpy.init()
    node = RoverSimRuntimeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
