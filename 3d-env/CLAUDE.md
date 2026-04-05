# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Full design reference: `initial-hl-design.md` (same directory)
> Phase 1 detail: `phase1-3D-Simulator.md`
> Canonical Phase 2 MQTT plan: `mqtt-plan-canonical-2026-04-05_00-58-36.md`

## Project Overview

This repo currently contains the **Remote Rover** 3D simulator. The simulator is the active implementation in this workspace.

1. **Simulator** — Python desktop simulator (Panda3D + `panda3d.bullet`): renders rover, runs physics, shows an ImGui menu/settings UI, and captures POV frames.
2. **Server / GCS** — described in design docs, but not implemented in this workspace.

All components communicate via an **external Mosquitto MQTT broker** (Docker on a separate Rocky Linux 9 machine).

## Commands

```bash
# Install simulator dependencies
pip install -r requirements.txt

# Run the simulator (software renderer — works everywhere)
python simulator/main.py

# Run with GPU (Windows)
run.bat

# Run with GPU (WSL2, requires NVIDIA GPU passthrough)
./run_gpu.sh

```

## Architecture

### Simulator (`simulator/`)

- **`main.py`** — Panda3D `ShowBase` entry point. GPU/WSL2 detection, PCF soft shadows (GPU only), stone obstacles (18 small + 6 large), trees (14), flip detection + auto-reset, game loop at 60 FPS.
- **`terrain.py`** — Procedural multi-octave heightmap (160×160 vertices, 200 m × 200 m). `BulletHeightfieldShape` collision mesh. `height_at(x, y)` bilinear query.
- **`rover.py`** — `BulletVehicle` with 4-wheel raycast suspension. Dynamic rigid body (130 kg). Engine force blending, anti-wheelie, ground-stick downforce. Exposes `.pos` (Vec3), `.heading` (°), `.speed` (km/h).
- **`camera.py`** — Orbital follow cam (right-click + scroll) + POV cam (V key). POV uses a 640×480 offscreen `GraphicsBuffer`; `pov_buffer` property exposes it for Phase 2 JPEG capture.
- **`gui.py`** — Telemetry HUD, top menu bar, and bottom status bar.
- **`settings_gui.py`** — ImGui settings windows for MQTT, key bindings, appearance, and import/export.
- **`imgui_style.py`** — Shared ImGui theme, DPI scaling, and startup font selection helpers.
- **`shadow_pcf.vert`** / **`shadow_pcf.frag`** — Custom GLSL PCF soft-shadow shaders (GPU mode only).

### Key Constraints

- Use **`panda3d.bullet`** (built into Panda3D) — do NOT use the standalone `pybullet` PyPI package.
- Keep each file focused — no premature abstraction.

### Controls (simulator)

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
| Phase 1 | 3D Simulator (standalone desktop) | ✅ Complete |
| Phase 2 | MQTT bridge in simulator (`mqtt_bridge.py`) | ✅ Implemented (control+state) |
| Phase 3 | Relay server + GCS web app | 🔲 Planned only |
| Phase 4 | Multi-GCS + peripheral devices | 🔲 Future |

## Phase 2 — MQTT Integration (implemented baseline)
Use `mqtt-plan-canonical-2026-04-05_00-58-36.md` as the source of truth.
Key decisions:
- Single control frame topic and single state frame topic.
- Configurable defaults: control rate 20 Hz, telemetry rate 2 Hz, failsafe 250 ms.
- Last-writer-wins arbitration between local keyboard and MQTT.
- Camera frame transport is out of Phase 2 scope (metadata only in state).

## Phase 3 — Server + GCS Web App

Documented in `initial-hl-design.md`, but not yet implemented here.

## MQTT Topic Structure

Topic prefix (`/remote-rover-01/`) is configurable per rover instance. All topics use QoS 0 (fire-and-forget). No trailing slash in prefix.

**Legacy sample topics (historical; superseded by canonical Phase 2 plan):**
```
/remote-rover-01/controls/throttle    {"value": 0.8}      ← subscribed by simulator
/remote-rover-01/controls/steering    {"value": -0.5}     ← subscribed by simulator
/remote-rover-01/controls/brake       {"value": 1.0}      ← subscribed by simulator
/remote-rover-01/telemetry/position   {"x": 1.2, "y": 3.4, "z": 0.1}   ← published by simulator (2 Hz)
/remote-rover-01/telemetry/heading    {"deg": 45.2}       ← published by simulator (2 Hz)
/remote-rover-01/video/pov            [JPEG binary]       ← published by simulator (10 FPS)
```

**Future (Phase 4+):**
```
/remote-rover-01/telemetry/imu        {"accel": {...}, "gyro": {...}}
/remote-rover-01/telemetry/gps        {"lat": ..., "lon": ..., "alt": ...}
/remote-rover-01/configs/...          configuration updates
```
