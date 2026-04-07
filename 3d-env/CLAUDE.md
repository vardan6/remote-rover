# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Full design reference: `initial-hl-design.md`
> Phase 1 detail: `phase1-3D-Simulator.md`
> Canonical Phase 2 MQTT plan: `mqtt-plan-canonical-2026-04-05_00-58-36.md`
> Current project status: `../PROJECT_REVIEW_AND_CURRENT_STATE.md`

## Project Overview

This workspace now contains the simulator plus the browser-facing GCS under the shared `remote-rover/` repository root.

1. **Simulator** — Python desktop simulator (Panda3D + `panda3d.bullet`): renders rover, runs physics, shows an ImGui menu/settings UI, captures POV frames, and publishes control, telemetry, and video over MQTT.
2. **Server / GCS** — implemented in `../gcs_server/`: FastAPI backend + static web UI that publishes control and renders telemetry/video from MQTT.

All components communicate via an external MQTT broker.

## Commands

```bash
# Install simulator dependencies
pip install -r requirements.txt

# Run the simulator
python simulator/main.py

# Run with GPU (Windows)
run.bat

# Run with GPU (WSL2, requires NVIDIA GPU passthrough)
./run_gpu.sh
```

## Architecture

### Simulator (`simulator/`)

- **`main.py`** — Panda3D `ShowBase` entry point, game loop, MQTT arbitration, telemetry publication, and POV JPEG publication.
- **`terrain.py`** — procedural heightmap terrain and Bullet collision mesh.
- **`rover.py`** — `BulletVehicle` rover implementation and drive model.
- **`camera.py`** — follow cam + POV cam with offscreen buffer used for MQTT frame capture.
- **`gui.py`** — telemetry HUD, top menu bar, and bottom status bar.
- **`settings.py`** — shared runtime config loading from `../config/` plus simulator UI settings.
- **`settings_gui.py`** — ImGui settings windows for MQTT, key bindings, appearance, and import/export.
- **`imgui_style.py`** — ImGui theme, DPI scaling, and font helpers.
- **`mqtt_bridge.py`** — simulator MQTT bridge for control, telemetry, and camera frame publishing.

### GCS (`../gcs_server/`)

- **`app.py`** — FastAPI app, routes, and WebSocket endpoint.
- **`runtime.py`** — runtime assembly for services.
- **`mqtt_service.py`** — MQTT subscription/publication logic.
- **`control.py`** — browser control loop and controller lease handling.
- **`state.py`** — in-memory runtime state store.
- **`video.py`** — MQTT camera frame decoding helper.

### Key Constraints

- Use **`panda3d.bullet`** rather than standalone `pybullet`.
- Keep simulator UI-only settings in `simulator/settings.json`.
- Keep shared runtime config in `../config/common.local.json` with the example file as fallback.

## Controls (simulator)

| Key | Action |
|-----|--------|
| ↑ or W | Throttle forward |
| ↓ or S | Throttle backward |
| ← or A | Steer left |
| → or D | Steer right |
| Right-click + drag | Orbit follow camera |
| Scroll wheel | Zoom follow camera |
| V | Toggle follow / POV camera |
| Escape | Quit |
| Simulation menu → Restart | Teleport rover back to spawn |

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | 3D Simulator (standalone desktop) | Complete |
| Phase 2 | MQTT bridge in simulator (`mqtt_bridge.py`) | Implemented |
| Phase 3 | Relay server + GCS web app | Implemented bootstrap version |
| Phase 4 | Multi-GCS + production media path | Future |

## Current Gaps

- Redis-backed distributed runtime state
- production WebRTC transport
- authentication and authorization
