# Documentation Status Audit

Status date: 2026-05-03.

## Canonical Documentation Set

Use `docs/` as the source of truth for current architecture, implementation status, operations, and plans.

Current canonical entrypoints:
- `docs/README.md`
- `docs/project-overview.md`
- `docs/current-state.md`
- `docs/architecture.md`
- `docs/implementation-roadmap.md`
- `docs/operations/run-and-config.md`
- `docs/simulation-platform-plan.md`
- `docs/rover-sim-next-phase-1-checklist.md`

Subproject READMEs remain useful entrypoints, but they should point back to `docs/` for current status.

## Review Coverage

Repository-authored markdown was reviewed across:
- repository root
- `docs/`
- `docs/3d-env/`
- `docs/gcs_server/`
- `3d-env/`
- `gcs_server/`
- `rover-sim-next/`
- `config/`

Virtual environment and third-party package markdown files under `.venv*` directories were excluded from the project-documentation review.

## Implementation Status Summary

Implemented and code-backed:
- `3d-env` Panda3D simulator runtime with local and MQTT control paths
- simulator telemetry and MQTT camera-frame publication
- GCS FastAPI app, static dashboard, WebSocket updates, browser control ownership, and MQTT control publishing
- MQTT setup/settings UI with runtime GCS reconnect
- GCS presence publishing used by simulator telemetry/camera publish gating
- SQLite-backed GCS replay/session storage
- replay APIs and separate replay page
- first Leaflet-based replay map using scene-map data
- explicit terrain scene manifest at `config/terrain_scene.v1.json`
- terrain manifest generator and validator tools
- simulator and GCS consumers for the terrain scene manifest
- config-backed backend identity with `3d-env` and `rover-sim-next` options

Partially implemented:
- replay/logging: GCS-side telemetry/control/runtime/camera-timing logging exists; synchronized recorded video playback does not
- map support: replay map exists; live dashboard map does not
- simulator backend transition: `rover-sim-next` scaffold exists; real simulator runtime does not
- geospatial support: current deterministic pseudo-GPS/local tangent-plane compatibility exists; full geospatial model does not

Not implemented:
- working `rover-sim-next` ROS 2/Gazebo backend
- authoritative CAD/asset import and replacement pipeline
- simulator-side logging architecture
- WebRTC or production media transport
- Redis/shared-state GCS backend
- authentication and authorization
- production deployment/secrets/config lifecycle

## Plan Alignment Decisions

Active plan direction:
- keep `3d-env` as the current runnable simulator
- keep `gcs_server` as the current operator-facing application
- make `rover-sim-next` the immediate next implementation milestone
- defer additional replay, live map, synchronized video, and production media work until after `rover-sim-next` works end to end with the GCS

This is reflected in:
- `docs/current-state.md`
- `docs/implementation-roadmap.md`
- `docs/simulation-platform-plan.md`
- `docs/simulation-platform-plan-review.md`
- `docs/rover-sim-next-phase-1-checklist.md`

## Archived Or Removed From Active Surface

Non-authoritative scratch, historical, and superseded markdown files were moved under `docs/archive/` instead of being deleted.

Archived groups:
- `docs/archive/root/`: former root-level plan/status snapshots
- `docs/archive/3d-env/`: scratch notes and old conversation notes
- `docs/archive/gcs_server/`: legacy GCS spec/scratch notes
- `docs/archive/rover-sim-next/`: simulator selection commentary superseded by current simulator plan docs

Historical phase documents that still live in `3d-env/` remain clearly labeled as historical or frozen references.

## Verification Performed

Checked by repository inspection:
- markdown inventory and active/historical classification
- code paths for GCS replay, terrain scene map, MQTT service, telemetry normalization, WebSocket handling, video frame decoding, and backend identity config
- `rover-sim-next` scaffold files and absence of a complete runnable simulator backend

Checks still worth running before a release or demo:
- full GCS startup with a reachable MQTT broker
- full `3d-env` simulator startup in the intended GPU/display environment
- browser dashboard control/telemetry/video loop
- replay recording and playback with a real session
