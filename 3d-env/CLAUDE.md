# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Full design reference: `initial-hl-design.md`
> Phase 1 detail: `phase1-3D-Simulator.md`
> Canonical Phase 2 MQTT plan: `mqtt-plan-canonical-2026-04-05_00-58-36.md`
> Current documentation entry point: `../docs/README.md`

## Project Overview

This workspace now contains the simulator plus the browser-facing GCS under the shared `remote-rover/` repository root.

1. **Simulator** — Python desktop simulator (Panda3D + `panda3d.bullet`): renders rover, runs physics, shows an ImGui menu/settings UI, captures POV frames, and publishes control, telemetry, and video over MQTT.
2. **Server / GCS** — implemented in `../gcs_server/`: FastAPI backend + static web UI that publishes control and renders telemetry/video from MQTT.

All components communicate via an external MQTT broker.

## Commands

```bash
# Run with Linux / native WSL Python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python simulator/main.py

# Linux / WSL helper launcher
./run.sh

# Run with Windows GPU Python
python -m venv .venv-gpu
.\.venv-gpu\Scripts\python -m pip install -r requirements.txt
run.bat

# Run from WSL through the Windows GPU env
./run_gpu.sh

# Regenerate and validate the explicit terrain scene manifest
cd ..
python3 tools/generate_terrain_scene.py
python3 tools/validate_terrain_scene.py
```

## Architecture

### Simulator (`simulator/`)

- **`main.py`** — Panda3D `ShowBase` entry point, game loop, MQTT arbitration, telemetry publication, and POV JPEG publication.
- **`terrain.py`** — manifest-backed heightfield terrain, road coloring, and Bullet collision mesh.
- **`../config/terrain_scene.v1.json`** — explicit terrain/object source of truth consumed by the simulator and GCS scene map.
- **`../tools/generate_terrain_scene.py`** — transition generator from the legacy compact terrain seed.
- **`../tools/validate_terrain_scene.py`** — terrain scene validation check.
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
- Do not hard-code terrain object names, coordinates, counts, or dimensions in runtime scripts; put terrain definition data in `../config/terrain_scene.v1.json`.

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
