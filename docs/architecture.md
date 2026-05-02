# Architecture

## System Overview

The current system is organized as two applications plus a shared runtime configuration layer.

```text
Browser Operator
  -> HTTP / WebSocket
GCS Server
  -> MQTT Broker
3D Simulator
```

Repository structure:

```text
remote-rover/
  3d-env/
  gcs_server/
  config/
  tools/
  docs/
```

## Application Responsibilities

### 1. 3D Simulator

Location:
- `3d-env/`

Primary responsibilities:
- simulate rover motion and environment
- accept local keyboard input
- accept remote control from MQTT
- generate telemetry payloads
- capture simulated camera frames
- publish telemetry and camera frames when allowed by the telemetry policy
- expose operator settings for MQTT and simulator runtime behavior

### 2. GCS Server

Location:
- `gcs_server/`

Primary responsibilities:
- serve the browser UI
- manage browser WebSocket connections
- enforce single-controller ownership
- publish MQTT control frames
- subscribe to telemetry and camera topics
- relay telemetry and video to browser clients
- publish GCS presence information so the simulator can decide whether outbound publishing is needed
- expose browser-based MQTT setup and runtime reconfiguration

### 3. Shared Config

Location:
- `config/`

Primary responsibilities:
- keep simulator and GCS aligned on runtime contract values
- store shared MQTT topic names and rates
- store GCS host/port defaults
- store video mode defaults
- store the telemetry publishing policy and GCS presence topic settings

### 4. Terrain Scene Manifest

Location:
- `config/terrain_scene.v1.json`

Primary responsibilities:
- define the current terrain heightfield
- define roads, spawn points, and static world objects
- provide the shared map/scene source for both the simulator and GCS
- avoid hard-coded terrain object names, counts, coordinates, and dimensions in runtime scripts

## Data Flows

### Browser Control Flow

```text
Browser
  -> WebSocket control messages
GCS
  -> MQTT control/manual
Simulator
```

Current behavior:
- browsers never publish directly to MQTT
- the GCS owns control publication
- one browser holds the control lock at a time
- the GCS publishes control frames at `mqtt.control_hz`

### Telemetry Flow

```text
Simulator
  -> MQTT telemetry/state
GCS
  -> WebSocket telemetry
Browser
```

Current behavior:
- the simulator emits rover state payloads on the configured telemetry topic
- the GCS subscribes and tracks freshness
- browsers receive telemetry snapshots through the GCS

### Camera Flow

```text
Simulator POV buffer
  -> MQTT camera-feed
GCS
  -> WebSocket video_frame
Browser
```

Current behavior:
- the simulator captures JPEG frames from the POV camera
- the GCS decodes and relays frames to browsers
- this path is currently the implemented bootstrap solution

### GCS Presence Flow

```text
GCS
  -> MQTT gcs/presence/<gcs_id> (retained + periodic)
Simulator
```

Current behavior:
- the GCS publishes a retained presence record per GCS instance
- the simulator subscribes to the presence wildcard topic
- in `auto` mode, the simulator only publishes outbound data if at least one GCS presence record is active and fresh

## MQTT Contract Summary

Current shared topic model:
- `{topic_prefix}/{control_topic}`
- `{topic_prefix}/{state_topic}`
- `{topic_prefix}/{camera_topic}`
- `{topic_prefix}/{gcs_presence_topic}/{gcs_id}`

Default values from shared config:
- `topic_prefix`: `/projects/remote-rover`
- `control_topic`: `control/manual`
- `state_topic`: `telemetry/state`
- `camera_topic`: `camera-feed`
- `gcs_presence_topic`: `gcs/presence`

## Telemetry Publishing Policy

Current simulator policy values:
- `auto`
- `force_on`
- `force_off`

Policy evaluation:
- `force_on`: always publish outbound simulator telemetry and camera frames
- `force_off`: never publish outbound simulator telemetry and camera frames
- `auto`: publish only while at least one active GCS presence entry is fresh

Freshness source:
- the GCS publishes presence with a timestamp
- the simulator checks the timestamp age against `mqtt.gcs_presence_timeout_ms`

This design is more reliable than checking whether telemetry values changed, because a stationary rover can still have an active operator session.

## Runtime Boundaries

### In The Simulator

Current important modules:
- `simulator/main.py`: runtime loop, publish gating, control merge, status bar updates
- `simulator/mqtt_bridge.py`: MQTT client, topic subscription, presence tracking, publish helpers
- `simulator/gui.py`: top menu and status bar, including telemetry policy menu
- `simulator/settings_gui.py`: settings dialogs and MQTT config fields
- `simulator/terrain.py`: manifest-backed terrain heightfield, visual mesh, road coloring, and Bullet collision mesh
- `simulator/rover.py`: rover physics and motion

### In The GCS

Current important modules:
- `gcs_server/app.py`: FastAPI routes, WebSocket endpoint, runtime wiring
- `gcs_server/mqtt_service.py`: broker connection, subscriptions, control publish, presence publish
- `gcs_server/control.py`: control loop and held-button publishing
- `gcs_server/state.py`: in-memory runtime state and freshness tracking
- `gcs_server/ws.py`: browser connection manager
- `gcs_server/runtime.py`: service assembly and reconfiguration
- `gcs_server/scene_map.py`: scene-map payload from `config/terrain_scene.v1.json`

## Current Architectural Strengths

- applications are cleanly separated
- shared runtime contract is centralized
- browser clients are isolated from direct MQTT publication
- presence-based publish gating reduces unnecessary simulator bandwidth
- the system already demonstrates an end-to-end operator workflow

## Current Architectural Gaps

- no distributed state backend yet
- no auth boundary yet
- no production media transport yet
- no finalized multi-GCS operational model yet
- runtime config is still local-file based
