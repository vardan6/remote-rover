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

Implementation priority for the first usable milestone:
- implement the ROS 2 node set and real Gazebo launch flow
- add a first drivable rover description in `urdf/`
- add a first loadable development world in `worlds/`
- bridge simulator state and controls to the current MQTT contract
- provide enough camera compatibility for the current GCS workflow
- add deterministic startup and basic headless execution

Deferred until after the first working GCS-connected milestone:
- simulator-side replay/logging work
- richer live-map integration in the GCS
- authoritative CAD-derived asset replacement flow
- synchronized recorded video support
