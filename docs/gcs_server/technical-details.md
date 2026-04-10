# GCS Technical Details

## Runtime Model

The GCS is a FastAPI application with a WebSocket-driven browser UI.

The backend assembles four main runtime concerns:
- browser connection management
- in-memory state tracking
- MQTT runtime integration
- control publication loop

## HTTP And WebSocket Surface

Current important routes:
- `/`: dashboard page
- `/setup/mqtt`: MQTT setup page
- `/api/health`: health summary
- `/api/snapshot`: current runtime snapshot
- `/api/config`: raw loaded config
- `/api/mqtt-config`: get and update MQTT settings
- `/api/video-mode`: update video mode flags
- `/api/controller/take`: claim control
- `/api/controller/release`: release control
- `/ws`: browser WebSocket endpoint

## Control Model

Current control ownership model:
- one active browser client at a time
- other connected browsers may observe
- browser button states are collected by the GCS
- the GCS publishes MQTT control frames at `control_hz`

This keeps browser clients off the broker directly and gives the GCS a clean control-plane role.

## MQTT Runtime Behavior

### Subscriptions

The GCS subscribes to:
- `{topic_prefix}/{state_topic}`
- `{topic_prefix}/{camera_topic}`

### Publications

The GCS publishes:
- control frames to `{topic_prefix}/{control_topic}`
- presence frames to `{topic_prefix}/{gcs_presence_topic}/{gcs_id}`

### Presence Payload

Current presence payload includes:
- `gcs_id`
- `active`
- `timestamp`
- `browser_count`
- `active_controller_id`

Current `active` rule:
- active is true when at least one browser WebSocket is connected, unless a forced value is used during shutdown or will handling

## In-Memory State Model

The current local state backend tracks:
- latest telemetry payload
- latest video frame metadata
- broker connection status and freshness timestamps
- active controller and lease timing
- video mode settings

This is enough for the current single-process deployment model, but not enough for coordinated multi-instance operation.

## Frontend Delivery Model

Current frontend update channels:
- telemetry over WebSocket JSON
- broker status over WebSocket JSON
- controller state over WebSocket JSON
- video frames over WebSocket JSON carrying decoded MQTT-frame data

Current implemented video mode:
- ingest: `mqtt_frames`
- delivery: `websocket_mjpeg`

## Technical Gaps Still Open

- move runtime state to Redis or equivalent shared backend
- define multi-GCS presence semantics more explicitly
- secure configuration and control endpoints
- introduce a production-grade video transport path
