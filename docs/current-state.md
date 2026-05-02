# Current State

## Summary

The project currently consists of two working applications and one new simulator scaffold inside one repository:
- `3d-env/`: the simulator
- `gcs_server/`: the browser-facing Ground Control Station
- `rover-sim-next/`: the next simulator scaffold for the planned ROS 2 + Gazebo successor path

The main end-to-end MQTT control loop is implemented and usable today.
The main next implementation priority is now `rover-sim-next`, not additional replay work.

## Implemented Today

### End-To-End Rover Control

Implemented now:
- browser clients connect to the GCS over WebSocket
- one browser can hold the controller lock at a time
- the GCS publishes control frames over MQTT at the configured control rate
- the simulator subscribes to MQTT control and applies remote driving input
- local simulator keyboard input still works alongside MQTT according to the configured control behavior

### End-To-End Telemetry

Implemented now:
- the simulator publishes rover telemetry over MQTT
- the GCS subscribes to telemetry and relays it to connected browser clients
- the browser dashboard shows rover motion, heading, deterministic virtual GPS, camera mode, and power values
- the GCS tracks whether telemetry is fresh or stale
- the GCS normalizes telemetry for replay/session storage

### End-To-End Camera Feed

Implemented now:
- the simulator captures POV frames
- JPEG frames are published over MQTT
- the GCS subscribes to those frames
- the GCS relays frames to browsers using a WebSocket MJPEG-style path
- the browser dashboard displays the live simulated camera feed

This is a bootstrap media path, not the final intended production media design.

### Simulator World And Runtime

Implemented now:
- a deterministic `400 x 400` terrain
- explicit terrain/object source of truth at `config/terrain_scene.v1.json`
- two solar plants placed in separate valleys
- a central operations building
- connecting roads and driveable corridors
- larger trees and mixed small/large rocks
- follow and POV camera modes
- simulator settings windows and top menu controls

### Shared Runtime Configuration

Implemented now:
- shared config at `config/common.example.json`
- local overrides at `config/common.local.json`
- simulator and GCS both consume the shared MQTT and GCS runtime settings
- GCS can edit MQTT settings through a browser setup page and reconnect live
- GCS exposes config-backed simulator backend identity: `3d-env` or `rover-sim-next`

### GCS-Aware Telemetry Publishing

Implemented now:
- simulator outbound MQTT publishing is `disabled by default` in practice when `telemetry_policy` is `auto` and no active GCS is present
- the GCS publishes retained presence messages on a dedicated MQTT presence topic
- the simulator subscribes to GCS presence and only publishes telemetry and camera frames when at least one GCS presence entry is still fresh
- the simulator supports manual override through `telemetry_policy`

Current policies:
- `auto`: publish only when an active GCS is fresh
- `force_on`: always publish
- `force_off`: never publish outbound simulator telemetry or camera frames

This is the current bandwidth-saving mechanism for data-sensitive deployments.

### Logging And Replay

Implemented now:
- the GCS persists replay-capable session data to SQLite
- the GCS records telemetry, control frames, runtime events, and camera timing metadata
- the GCS exposes replay session APIs
- the GCS provides a separate replay page
- the replay page can load a recorded session and play back telemetry and runtime events
- the replay page includes a first Leaflet-based map playback view

Current storage model:
- session metadata is stored in SQLite
- telemetry, control, and runtime events are stored in SQLite
- camera timing metadata is stored in SQLite
- synchronized video file playback is not implemented yet

These capabilities now exist as groundwork, but they are not the current critical path.
The current critical path is turning `rover-sim-next` into a working simulator backend that can operate with the existing GCS.

### New Simulator Successor Scaffold

Implemented now:
- `rover-sim-next/` exists as a new simulator sub-project scaffold
- ROS 2 package metadata and Gazebo-oriented layout are present
- placeholder config, launch entrypoint, MQTT bridge module, `URDF` directory, and `SDF` world directory are present

This is not yet a working replacement simulator.
It is the repository starting point for the successor backend.

## Current Known Limitations

### 1. Media Transport Is Still A Bootstrap Path

Current video transport is:
- simulator MQTT JPEG frames
- GCS WebSocket browser delivery

This works for demonstration and development, but it is not the intended final architecture for scalable live video.

### 2. Live Map Is Not On The Main Dashboard Yet

Replay now has a first map view, but the live dashboard still does not have a dedicated map panel.

That means:
- recorded rover tracks can be viewed on a map in replay
- live rover map tracking is still a next step

This is no longer the immediate next step.
It should follow after `rover-sim-next` is functioning with the GCS.

### 3. GCS State Is Single-Instance Only

The current GCS runtime state is in memory.

That means:
- it works for a single running process
- it is not yet suitable for multiple coordinated GCS backend instances
- a proper shared backend such as Redis is still needed for scale-out

### 4. Authentication Is Not Implemented

There is currently no authentication or authorization layer for operators, observers, or configuration changes.

### 5. Multi-GCS Policy Is Only Partially Defined

The system now supports presence per GCS instance, but the broader operational model is not fully defined yet.

Still to define clearly:
- how multiple GCS instances should be identified in production
- which GCS roles are allowed to enable telemetry
- whether observer-only sessions should count as active for all deployments
- whether future real-rover mode should use the same publish gating policy as the simulator
- how replay/logging ownership should work if multiple GCS backends are later deployed

### 6. Configuration Management Is Still Local-File Based

The shared config model is practical for development, but it is still file-based and local.

It does not yet include:
- environment profiles
- secret management
- deployment-specific config packaging
- admin authorization for runtime changes

### 7. `rover-sim-next` Is Still A Scaffold

The new simulator successor project now exists, but it is not yet a functioning simulator backend.

Not implemented yet in `rover-sim-next`:
- real rover simulation
- real Gazebo world integration
- real MQTT bridge behavior
- authoritative robot description
- project asset pipeline
- headless simulation workflow

This is the main implementation gap in the repository.

## Current Implementation Priority

The next work should focus on `rover-sim-next` in this order:
- make it launch as a real simulator process
- make it accept control from the existing GCS
- make it emit telemetry compatible with the existing GCS
- make it provide at least the minimum camera compatibility needed for the current operator workflow
- establish the coordinate and asset structure needed for later map, CAD, and replay work

Replay, simulator-side logging, richer map UI, and synchronized video remain important, but they should follow this simulator integration milestone.

## What Makes The Current State Presentable

The project is already in a solid demonstration state because the full operator loop is visible and understandable.

You can show:
- a simulated rover world
- a browser-based control station
- live control handoff and locking
- live telemetry in the dashboard
- live simulated camera feed
- bandwidth-aware publish suppression when no GCS is active
- persistent GCS-side session logging
- replay page with timeline and map playback
- explicit backend identity for current and next simulator tracks
- shared terrain scene manifest used by both the simulator and GCS scene-map payload

That is enough to present the current system as a functioning integrated prototype with a clear path toward production hardening.

## Recommended Message When Presenting The Project

A precise way to describe the current state is:

> Remote Rover is currently a working integrated prototype with a Panda3D simulator, a browser-based Ground Control Station, MQTT-based control and telemetry, a bootstrap video path, and first-generation GCS-side session replay. It already supports live control, telemetry, camera streaming, bandwidth-aware simulator publishing based on active GCS presence, and recorded replay of telemetry/control/event history. The main next step is completing `rover-sim-next` as a working successor backend that integrates with the existing GCS, after which live map, richer replay, improved media transport, and production hardening can continue.
