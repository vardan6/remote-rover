# Phase 1 — 3D Rover Simulator

> Historical Phase 1 snapshot.
> For current MQTT behavior and Phase 2 contracts, use `mqtt-plan-canonical-2026-04-05_00-58-36.md`.
> For current workspace structure, use `../README.md` and `../remote_rover_architecture_and_implementation_plan.md`.

## Overview

A real-time 3D rover simulator built with Python, Panda3D, and Bullet physics.

Phase 1 established:
- procedural terrain
- rover physics and drive model
- local keyboard driving
- follow and POV camera modes
- on-screen telemetry HUD
- detached native settings windows backed by Tk

MQTT functionality was added after this phase.

## Current Simulator Location

- `3d-env/simulator/`

## How To Run

```bash
cd /mnt/c/Users/vardana/Documents/Proj/remote-rover/3d-env
pip install -r requirements.txt
python simulator/main.py
```

Optional GPU helpers:
- `run.bat`
- `run_gpu.sh`

## Main Simulator Modules

```text
simulator/
  main.py
  rover.py
  terrain.py
  camera.py
  gui.py
  settings.py
  settings_gui.py
  mqtt_bridge.py
```

## Phase 1 Scope Summary

Implemented in the original simulator phase:
- Panda3D `ShowBase` desktop application
- terrain mesh and Bullet collision heightfield
- BulletVehicle-style rover simulation
- follow camera and POV camera toggle
- local keyboard controls
- telemetry HUD and status bar
- native settings windows for simulator configuration

Added after Phase 1:
- MQTT control subscription
- MQTT telemetry publication
- shared GCS-related config keys in `simulator/settings.json`

## Notes

This document is intentionally brief and historical.
The current authoritative simulator/MQTT runtime behavior is defined by code plus:
- `mqtt-plan-canonical-2026-04-05_00-58-36.md`
- `../PROJECT_REVIEW_AND_CURRENT_STATE.md`
