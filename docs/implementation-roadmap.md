# Implementation Roadmap

## Roadmap Summary

Status basis date: 2026-05-03.

The current `3d-env` + `gcs_server` system already works as an integrated prototype. The immediate next implementation priority is making `rover-sim-next` a working simulator backend that can operate with the existing GCS. Production hardening remains important, but it should follow the successor-backend integration milestone.

## Priority 1: Make `rover-sim-next` A Working GCS-Compatible Backend

Goal:
- turn the current `rover-sim-next/` scaffold into a runnable simulator backend without breaking `3d-env`

Recommended work:
- implement the real ROS 2/Gazebo launch path
- add the first drivable rover model and loadable development world
- bridge current GCS MQTT control payloads into simulator actuation
- publish telemetry compatible with the current GCS and replay normalization layer
- provide a first compatible camera path or explicit interim stream
- carry backend identity, site origin, and coordinate settings through config and telemetry

Success criteria:
- `rover-sim-next` can be launched with one documented command
- the existing GCS can drive and display rover state from `rover-sim-next`
- `3d-env` remains runnable as the current working backend
- no GCS-side protocol rewrite is required for the first milestone

Detailed plan:
- [Simulation Platform Plan](./simulation-platform-plan.md)
- [rover-sim-next Phase 1 Checklist](./rover-sim-next-phase-1-checklist.md)

## Priority 2: Stabilize The Existing MQTT Bootstrap Path

Goal:
- keep the current working system reliable enough for repeatable demonstrations and internal use while `rover-sim-next` is being built

Recommended work:
- verify simulator publish gating under broker reconnect and retained-message edge cases
- verify GCS presence expiration behavior when browser sessions disconnect unexpectedly
- verify stale camera and stale telemetry handling in the GCS UI
- add more explicit runtime logging for broker reconnect, presence state changes, and control ownership transitions
- document the intended operator workflow for bandwidth-sensitive deployments

Success criteria:
- simulator does not keep publishing when no GCS is active unless manually overridden
- reconnect behavior is predictable and observable
- dashboard freshness indicators reflect actual runtime conditions

## Priority 3: Clarify Multi-GCS Policy

Goal:
- define how more than one GCS should behave before introducing distributed deployment

Questions that should be settled explicitly:
- what uniquely identifies a GCS instance in production
- whether any connected observer should count as an active GCS for telemetry enabling
- whether only controller-owning GCS instances should count as active
- how presence should behave when several browser clients are attached to different GCS instances
- whether there should be separate concepts for `observer present` and `telemetry requested`

Recommended output:
- one small design note that defines multi-GCS presence semantics and operator expectations

## Priority 4: Replace In-Memory GCS State With Shared State

Goal:
- support multi-instance deployment and more robust coordination

Recommended work:
- move controller lock and relevant runtime state to Redis
- define expiration, renewal, and ownership semantics centrally
- make WebSocket-serving instances stateless where possible

Benefits:
- enables horizontal scaling
- removes single-process coordination limits
- prepares the GCS for more realistic deployment

## Priority 5: Upgrade The Media Path

Goal:
- replace the current MQTT-frame bootstrap video path with a production-appropriate transport

Recommended target direction:
- WebRTC-based delivery

Possible shape:
- ingest: `whip`, `rtsp`, or another media-native path
- delivery: `webrtc_direct` or `webrtc_sfu`
- keep `mqtt_frames -> websocket_mjpeg` as a debug or fallback path during transition

Benefits:
- lower overhead for live video
- better latency and scalability characteristics
- cleaner separation between telemetry/control and media transport

## Priority 6: Security And Access Control

Goal:
- add a real security boundary before broader use

Recommended work:
- authentication for operators and observers
- authorization for control ownership and config updates
- auditability for control claim and release actions
- protection of configuration endpoints

## Priority 7: Operational Hardening

Goal:
- make the system easier to run consistently across developer and demo environments

Recommended work:
- formalize environment-specific config files or profiles
- improve run scripts and launcher documentation across Linux, Windows, and WSL
- add health and diagnostics notes for broker connectivity
- define deployment assumptions for simulator-only mode versus future real-rover mode

## Priority 8: Real Rover Adaptation Layer

Goal:
- make the architecture ready to support a real rover backend alongside the simulator

Recommended work:
- define a common vehicle contract layer where the simulator and real rover publish comparable telemetry
- separate simulator-specific data from vehicle-generic data where appropriate
- define which parts of the current GCS remain unchanged when the backend is no longer simulated

## Recommended Presentation Framing

When presenting the roadmap, describe it this way:

1. The prototype loop is already working.
2. The next milestone is a working `rover-sim-next` backend beside the current `3d-env` simulator.
3. After that, the main production gaps are distributed state, media transport, security, and deployment hardening.
4. The current architecture is already split correctly, so the next work is implementation and hardening rather than repo restructuring.
