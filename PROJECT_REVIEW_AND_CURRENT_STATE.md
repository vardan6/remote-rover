# Project Review And Current State

## Summary

The project now has the right high-level split and the correct repository root:
- the simulator remains under `3d-env/`
- the Ground Control Station is separated into `gcs_server/`
- the active git repository is rooted at `remote-rover/`

That separation is correct and matches the intended system boundaries better than keeping the GCS under `3d-env/`.

## What Is Good

- `3d-env/` now remains focused on the simulator runtime and simulator documentation.
- `gcs_server/` is physically separated and no longer mixed into the 3D environment tree.
- The GCS reads the simulator settings file through an explicit path in `gcs_server/config.py`.
- MQTT topic naming is consistent across simulator and GCS:
  - `control/manual`
  - `telemetry/state`
  - `camera-feed`
- The simulator settings model now includes:
  - `mqtt.camera_topic`
  - `video.*`
  - `gcs.*`
- The simulator settings UI now exposes `camera_topic`, which closes the main config mismatch.
- The GCS runtime compiles cleanly after the split.
- The parent `remote-rover/` directory is now the correct place to commit and push from.

## Current Risks / Weak Spots

### 1. Shared config is practical, but temporary

The GCS currently reads and may persist settings back to:
- `config/common.local.json`

This is acceptable for now because it keeps MQTT topics and transport settings aligned in one common place, but it still mixes simulator and GCS runtime concerns into one shared JSON file.

Recommendation:
- later extract a root-level shared config file or shared config module
- keep simulator-specific UI settings inside `3d-env/simulator/settings.json`

### 2. Video path is only partially complete

Current state:
- GCS can subscribe to MQTT camera frames
- GCS can render camera frames received through MQTT
- simulator does not yet publish actual camera frames to `camera-feed`

Conclusion:
- the end-to-end video pipeline is architected but not fully functional yet

### 3. GCS state backend is single-instance only

Current state:
- GCS controller lock and runtime state use local memory

Impact:
- works for a single process
- not safe for multi-worker or multi-instance deployment

Recommendation:
- add Redis before any real scale-out deployment

## Path And File Review

Verified correct:
- `remote-rover/gcs_server/config.py` points to `remote-rover/config/common.local.json` with fallback to `remote-rover/config/common.example.json`
- `remote-rover/requirements-gcs.txt` contains only GCS dependencies
- `remote-rover/3d-env/requirements.txt` no longer contains web-server dependencies
- `remote-rover/gcs_server/GCS-web-app.md` exists with the GCS code
- root `.gitignore` now excludes local editor/runtime state

## Useful Conclusions

1. The simulator and GCS should remain separate applications.
2. Separate Python environments are the correct default.
3. Shared MQTT topic config is useful now, and it is no longer stored in simulator-owned files.
4. The highest-value next implementation step is simulator camera frame publishing.
5. The repository root is now in the right place; the next cleanup is config extraction, not repo restructuring.

## Recommended Next Steps

1. Add simulator camera frame publishing to `mqtt.camera_topic`.
2. Add Redis-backed GCS state before multi-user deployment.
3. Add a production media path (`webrtc_sfu`) after MQTT-frame bootstrap is validated.
4. Later split shared config into more explicit domains if the single common file becomes too broad.
