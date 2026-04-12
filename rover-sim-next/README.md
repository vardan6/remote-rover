# rover-sim-next

`rover-sim-next` is the next simulator backend scaffold for the Remote Rover project.

This directory is the successor track to `3d-env/`.
It is intended to evolve toward a ROS 2 + Gazebo simulator that can eventually substitute the real rover for faster development, testing, and debugging cycles.

## Current Scope

This initial scaffold establishes:
- ROS 2 package structure
- a Gazebo launch entrypoint
- a simulator config file aligned to the existing MQTT/GCS contract
- a placeholder MQTT bridge node
- a placeholder rover model directory for future `URDF`/`Xacro`
- a placeholder world directory for future modular `SDF` worlds

## Contract Goal

During transition, this simulator should preserve compatibility with the existing GCS MQTT contract:
- `{topic_prefix}/{control_topic}`
- `{topic_prefix}/{state_topic}`
- `{topic_prefix}/{camera_topic}`
- `{topic_prefix}/{gcs_presence_topic}/{gcs_id}`

## Planned Next Work

- implement the ROS 2 node set
- add rover description in `urdf/`
- add world composition in `worlds/`
- bridge simulator state and controls to the current MQTT contract
- add headless and repeatable recording-oriented launch modes
