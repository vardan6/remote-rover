# 3D Simulator Documentation

## Purpose

The simulator is the vehicle-side runtime of the project.

It provides:
- a simulated rover with physics and terrain interaction
- a local operator view for simulator-side testing
- MQTT control intake
- telemetry generation
- simulated camera output
- settings and diagnostics needed during development and demos

## What It Does Today

Implemented today:
- Panda3D desktop simulator with Bullet physics
- keyboard driving
- follow and POV camera modes
- telemetry HUD and status bar
- deterministic large terrain with mission-style landmarks
- MQTT control subscription
- MQTT telemetry publication
- MQTT camera-frame publication
- settings UI for MQTT, key bindings, appearance, import/export
- menu control for telemetry publishing policy
- automatic suppression of outbound publishing when no active GCS is available in `auto` mode

## Main Operator-Relevant Behavior

### Control Sources

The simulator currently supports:
- local keyboard input
- MQTT control input from the GCS

Remote control safety behavior:
- remote MQTT input has a failsafe timeout
- stale control input is neutralized

### Telemetry Publishing Policy

The simulator now has a policy that determines whether it sends outbound MQTT telemetry and camera frames.

Current policies:
- `auto`
- `force_on`
- `force_off`

Meaning:
- `auto`: publish only while at least one GCS instance is active and fresh on the presence topic
- `force_on`: always publish
- `force_off`: never publish

This is the current solution for reducing unnecessary data usage.

### Camera Behavior

The simulator has two local viewing modes:
- follow
- POV

For remote delivery, the simulator currently publishes POV JPEG frames over MQTT when video is enabled and telemetry publish policy allows outbound traffic.

## Terrain And Visual World

Current world includes:
- a larger `400 x 400` terrain area
- an explicit `config/terrain_scene.v1.json` terrain scene manifest
- deterministic valley and hill shaping
- two solar plant areas
- one central operations building
- connecting roads and flattened vehicle corridors
- larger trees and mixed-size rocks

This makes the simulator better suited for presentations and route-driving demonstrations than the earlier simple terrain.

The simulator runtime reads terrain heightfield data, roads, spawn points, and static object definitions from the manifest. Object names, counts, coordinates, and dimensions should not be hard-coded in simulator scripts.

## Main Files

- `simulator/main.py`: main runtime loop, telemetry generation, publish gating, integration
- `simulator/mqtt_bridge.py`: MQTT client, control subscription, state publish, camera publish, GCS presence tracking
- `simulator/gui.py`: menu bar, status bar, telemetry overlay
- `simulator/settings_gui.py`: settings windows and persistence
- `simulator/terrain.py`: manifest-backed terrain heightfield, visual mesh, road coloring, and Bullet collision mesh
- `simulator/rover.py`: rover dynamics
- `simulator/camera.py`: follow/POV camera handling and POV buffer capture

## How To Run

See the shared operations guide:
- [Run And Config Guide](../operations/run-and-config.md)

For deeper technical notes:
- [Simulator Technical Details](./technical-details.md)
