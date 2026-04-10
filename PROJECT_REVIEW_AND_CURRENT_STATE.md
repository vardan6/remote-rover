# Project Review And Current State

> Historical review snapshot.
> For the current presentation-ready documentation set, start with:
> - `docs/README.md`
> - `docs/current-state.md`
> - `docs/architecture.md`
> - `docs/implementation-roadmap.md`

## Summary

The project structure is now correct and the MQTT bootstrap path is implemented end to end:
- the simulator remains under `3d-env/`
- the Ground Control Station is separated into `gcs_server/`
- the active git repository is rooted at `remote-rover/`
- shared runtime config lives in `config/`
- simulator control, telemetry, and camera-frame publishing are all present
- the simulator world has been upgraded (April 8, 2026) to a larger deterministic terrain with mission-style map features

That split matches the intended system boundaries better than keeping the GCS under `3d-env/`.

## What Is Good

- `3d-env/` remains focused on the simulator runtime and simulator documentation.
- `gcs_server/` is physically separated and no longer mixed into the 3D environment tree.
- The simulator and GCS both read shared runtime config from `config/common.local.json` with `config/common.example.json` as fallback.
- MQTT topic naming is consistent across simulator and GCS:
  - `control/manual`
  - `telemetry/state`
  - `camera-feed`
- The shared config model includes:
  - `mqtt.camera_topic`
  - `video.*`
  - `gcs.*`
- The simulator settings UI exposes the shared MQTT/control fields.
- The simulator publishes JPEG frames from the POV camera buffer over MQTT when video is enabled and ingest mode is `mqtt_frames`.
- The simulator 3D environment now includes:
  - `400 x 400` terrain (`2x` each side vs previous map)
  - increased terrain mesh resolution (`160 -> 320`)
  - deterministic high-hill / dual-valley shaping
  - two valley solar plants, one central building, and explicit rover road corridors
  - larger trees and mixed large/small stone fields with placement keepout around roads and facilities
- The GCS subscribes to MQTT camera frames and relays them to browsers in `websocket_mjpeg` mode.
- The GCS includes a dedicated MQTT setup page that edits shared `mqtt.*` config and reconnects the broker client live.
- The GCS dashboard now includes persisted appearance/theme settings.
- The parent `remote-rover/` directory is the correct place to commit and push from.

## Current Risks / Weak Spots

### 1. Shared config is practical, but broad

Current state:
- runtime settings are shared through `config/common.local.json`
- simulator UI-only settings still live in `3d-env/simulator/settings.json`

Recommendation:
- keep simulator UI settings local to `3d-env/`
- later split shared runtime config into clearer domains if the single JSON file becomes too broad

### 2. Video path is implemented, but still a bootstrap transport

Current state:
- GCS subscribes to MQTT camera frames
- GCS renders camera frames received through MQTT
- simulator publishes JPEG frames from the Panda3D POV buffer to `camera-feed`

Conclusion:
- the end-to-end video pipeline now works
- the current transport is still a simple MQTT-frame bootstrap path, not a production media architecture

### 3. GCS state backend is single-instance only

Current state:
- GCS controller lock and runtime state use local memory

Impact:
- works for a single process
- not safe for multi-worker or multi-instance deployment

Recommendation:
- add Redis before any real scale-out deployment

### 4. Runtime config editing is now simpler but still local-file based

Current state:
- GCS can read/update MQTT host, port, topics, client ID, and control rate from browser setup UI
- Updates are written to `config/common.local.json` and applied immediately via runtime reconnect

Impact:
- operator workflow is better for broker changes
- production secrets/config lifecycle is still unmanaged (no secret manager, no environment profile system)

## Path And File Review

Verified correct:
- `remote-rover/gcs_server/config.py` points to `remote-rover/config/common.local.json` with fallback to `remote-rover/config/common.example.json`
- `remote-rover/gcs_server/requirements-gcs.txt` contains only GCS dependencies
- `remote-rover/3d-env/requirements.txt` contains simulator dependencies
- `remote-rover/3d-env/simulator/terrain.py` defines deterministic dual-plant world layout and drivable road flattening
- `remote-rover/3d-env/simulator/main.py` builds solar plants, operations building, roads, and updated decor placement
- `remote-rover/gcs_server/GCS-web-app.md` exists with the GCS code
- root `.gitignore` excludes local editor/runtime state

## Useful Conclusions

1. The simulator and GCS should remain separate applications.
2. Separate Python environments are the correct default.
3. Shared MQTT topic config is useful now and is no longer stored in simulator-owned files.
4. The MQTT bootstrap path is now working end to end for control, telemetry, and video.
5. The repository root is in the right place; the next cleanup is config ownership and runtime hardening, not repo restructuring.

## Recommended Next Steps

1. Verify broker reconnect, freshness, and stale-frame behavior under disconnect/reconnect conditions.
2. Add Redis-backed GCS state before multi-user or multi-instance deployment.
3. Add a production media path (`webrtc_sfu` or equivalent) after the MQTT-frame bootstrap is validated.
4. Later split shared config into more explicit domains if the single common file becomes too broad.
