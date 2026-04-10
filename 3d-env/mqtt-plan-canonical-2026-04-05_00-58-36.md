# MQTT Phase 2 Canonical Plan (Frozen)
Date: 2026-04-05 00:58:36 (+04)

> Historical frozen Phase 2 contract.
> For the current system documentation, start with `../docs/README.md`.
> The current codebase has moved beyond this exact scope and now includes MQTT camera-frame publication in later work.
> Keep this file as the Phase 2 control/telemetry contract reference, not as a complete description of current runtime behavior.

## 1. Scope (Documentation Freeze)
This plan defines MQTT integration scope for the 3D simulator only.
This document is rigid for implementation next steps and supersedes prior MQTT planning notes.
No code behavior is changed by this document itself.

## 2. Phase 2 Objectives
- Add MQTT client bridge in simulator.
- Receive remote control commands.
- Publish rover state telemetry.
- Keep current local keyboard controls and merge with MQTT control using last-writer-wins.
- Do not implement camera frame transport over MQTT in this phase.

## 3. MQTT Contracts

### 3.1 Topic Prefix
- Configurable `topic_prefix` (existing settings field).

### 3.2 Control Topic (Single Frame)
- Topic: `{topic_prefix}/{control_topic}`
- Default `control_topic`: `control/manual`
- Payload JSON (hybrid support):
  - `mode`: `"analog"` or `"digital"`
  - `throttle`: float `[-1.0, 1.0]` (optional in digital mode)
  - `steering`: float `[-1.0, 1.0]` (optional in digital mode)
  - `buttons`: object with booleans:
    - `forward`, `backward`, `left`, `right`, `stop`, `camera_toggle`
  - `source`: string (optional)
  - `timestamp`: number (optional)

### 3.3 State Topic (Single Frame)
- Topic: `{topic_prefix}/{state_topic}`
- Default `state_topic`: `telemetry/state`
- Payload JSON includes:
  - Pose/orientation/speed
  - IMU accel+gyro
  - GPS-like coordinates + altitude/barometer
  - Camera status metadata (enabled/mode), no image bytes
  - Power fields (constant placeholders for now):
    - battery level
    - voltage
    - current
    - temperature
  - `timestamp`

## 4. Control Mechanics
- Hybrid control is supported.
- Digital mode mapping uses fixed preset step values:
  - forward/backward -> throttle step
  - left/right -> steering step
  - release/stop -> neutral axis
- Analog mode uses proportional throttle/steering values.
- Arbitration policy: last-writer-wins between local and MQTT input.
- Failsafe: if control frame age > `250 ms`, neutralize remote throttle/steering.

## 5. Settings Changes (Phase 2)
Add or finalize MQTT/control settings in `simulator/settings.json` model/UI:
- `control_topic` (default `control/manual`)
- `state_topic` (default `telemetry/state`)
- `control_hz` (default `20`, configurable)
- `telemetry_hz` (default `2`, configurable)
- `failsafe_timeout_ms` (default `250`)
- `control_mode` (default `hybrid`)
- `digital_throttle_step`
- `digital_steer_step`
- `video_endpoint` (placeholder only; no MQTT video transport in Phase 2)

## 6. Non-Goals (Explicit)
- No MQTT camera frame publishing in this phase.
- No server/GCS implementation changes in this phase.
- No protocol expansion beyond current MQTT scope.
- No migration from `simulator/settings.json` to `config.json` in this phase.

## 7. Acceptance Criteria
- Rover is drivable through MQTT control topic using hybrid frame schema.
- Rover state is published on a single state topic at configurable default `2 Hz`.
- Control publish rate setting default is `20 Hz`.
- Remote failsafe neutralization triggers at `250 ms` silence.
- Existing local keyboard controls continue to work under last-writer-wins policy.
- Settings persist via existing simulator settings storage.

## 8. Implementation Safety Rule
This plan is frozen for Phase 2 execution.
Any change to contracts/rates/topic shape requires explicit plan revision first.
