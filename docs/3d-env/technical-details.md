# Simulator Technical Details

## Runtime Structure

The simulator is a Panda3D application centered on `simulator/main.py`.

Important responsibilities inside the runtime:
- build terrain and scene geometry from `config/terrain_scene.v1.json`
- create rover physics objects
- merge local and MQTT control input
- generate telemetry payloads
- publish telemetry and camera frames through the MQTT bridge
- expose menu and settings behavior

## Terrain Scene Data

Current terrain and static scene data are manifest-driven.

Runtime source:
- `config/terrain_scene.v1.json`

Generator and validation:
- `tools/generate_terrain_scene.py`
- `tools/validate_terrain_scene.py`

`simulator/terrain.py` reads the explicit heightfield and road definitions. `simulator/main.py` reads the explicit object list and creates boxes, ellipsoid rocks, compound trees, collision proxies, and the configured spawn point.

The legacy compact file `config/terrain_scene.json` is only generator input during this transition. Runtime code should not use it directly.

## MQTT Integration

### Control Subscription

The simulator subscribes to:
- `{topic_prefix}/{control_topic}`

It accepts control frames with button-based and optional analog fields, then applies them according to the configured control mode and failsafe timeout.

### Telemetry Publication

The simulator publishes telemetry payloads to:
- `{topic_prefix}/{state_topic}`

The payload currently includes:
- timestamp
- position
- deterministic virtual GPS derived from the terrain georeference
- orientation
- IMU placeholders and angular velocity
- barometer altitude
- speed and velocity
- camera mode metadata
- power placeholder values

### Camera Publication

The simulator publishes JPEG bytes to:
- `{topic_prefix}/{camera_topic}`

Current source:
- POV offscreen buffer capture

### GCS Presence Tracking

The simulator subscribes to:
- `{topic_prefix}/{gcs_presence_topic}/+`

It stores presence by `gcs_id` and considers a GCS active only when:
- the payload says `active: true`
- the payload contains a recent timestamp
- the timestamp age is within `gcs_presence_timeout_ms`

## Publish Gating Logic

The simulator uses one gate for all outbound MQTT publishing.

Current gate behavior:
- state telemetry publish is blocked when policy does not allow it
- camera frame publish is blocked when policy does not allow it

This matters because disabling only state telemetry would still leak bandwidth through camera frames.

## UI Surface

Current operator-visible UI related to MQTT includes:
- bottom status bar with MQTT state and telemetry policy/effective state
- menu item `Settings -> Telemetry Policy`
- MQTT settings dialog fields for:
  - broker host and port
  - topics
  - rates
  - control mode
  - telemetry policy
  - GCS presence topic
  - GCS presence timeout

## Current Technical Limitations

- camera transport is still MQTT JPEG publishing
- there is no dedicated simulator-side diagnostics screen for presence entries yet
- shared runtime config is practical but still broad
- power values are placeholders rather than a modeled vehicle power system

## Current Testing Reality

The current codebase supports real runtime testing, but the project still depends heavily on manual end-to-end validation for:
- broker reconnect behavior
- stale presence behavior
- video freshness
- cross-platform launcher behavior
