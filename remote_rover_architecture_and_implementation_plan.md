# Remote Rover — Current Architecture And Implementation Plan

## Current Architecture

The project is currently split into two applications under the `remote-rover/` workspace:

```text
remote-rover/
  3d-env/
    simulator/
    requirements.txt
  gcs_server/
    app.py
    static/
  requirements-gcs.txt
```

### 1. Simulator

Location:
- `3d-env/simulator/`

Responsibilities:
- rover physics and terrain simulation
- local keyboard driving
- camera mode switching
- telemetry collection
- MQTT control subscription
- MQTT telemetry publication

### 2. Ground Control Station

Location:
- `gcs_server/`

Responsibilities:
- browser UI serving
- MQTT subscription for telemetry and camera frames
- MQTT control publication
- active-controller lock
- broker status reporting
- video ingest/delivery mode selection

### 3. Shared Runtime Contract

Current shared config source:
- `config/common.local.json`
- fallback template: `config/common.example.json`

Shared MQTT topics:
- `{topic_prefix}/{control_topic}`
- `{topic_prefix}/{state_topic}`
- `{topic_prefix}/{camera_topic}`

Default values:
- `topic_prefix`: `/projects/remote-rover`
- `control_topic`: `control/manual`
- `state_topic`: `telemetry/state`
- `camera_topic`: `camera-feed`

## Current Implementation State

Implemented now:
- simulator MQTT control + telemetry bridge
- GCS web app split out of the simulator tree
- browser controller locking
- shared `camera_topic` config key
- `video.ingest_mode` and `video.delivery_mode` config keys
- separate dependency files for simulator and GCS

Not implemented yet:
- simulator camera frame publishing
- WebRTC delivery
- Redis-backed distributed GCS state
- auth/session security

## Recommended Execution Order

### Phase A: Finish the bootstrap path
- add simulator camera frame publishing to MQTT
- confirm end-to-end browser video rendering in the GCS
- verify topic freshness behavior under disconnect/reconnect conditions

### Phase B: Harden shared configuration
- keep shared runtime config in `config/`
- keep simulator UI config local to `3d-env/`
- keep runtime contracts documented in one current document

### Phase C: Prepare for scale-out
- add Redis-backed controller/state storage
- document single-instance vs multi-instance deployment modes
- add clearer operational logging for control ownership and broker transitions

### Phase D: Replace the bootstrap media path
- move from `mqtt_frames -> websocket_mjpeg` to a real WebRTC path
- keep the MQTT frame path available as a fallback/debug mode

## Structural Conclusion

The repository root is now correctly placed at `remote-rover/`.

That resolves the earlier tracking problem between:
- `3d-env/`
- `gcs_server/`
- root-level project documentation

The remaining structural improvement is not repo layout, but config ownership:
- simulator-specific settings should stay in `3d-env/`
- eventually shared MQTT/GCS config should move to a root-level shared config source
