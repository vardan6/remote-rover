> Deprecated: superseded for MQTT Phase 2 decisions by `mqtt-plan-canonical-2026-04-05_00-58-36.md`.
> Kept for historical context only.

# Phase 1 — 3D Rover Simulator (Qwen3 Version)

## Overview

Phase 1 implements a standalone Python desktop application that simulates a 3D rover environment using Panda3D and panda3d.bullet. The simulator features realistic terrain, physics-based rover movement, dual camera systems, and real-time telemetry display.

This phase focuses solely on the local simulation without any networking capabilities. All controls are handled through local keyboard input.

## Key Features

### 3D Environment
- Procedurally generated terrain with gentle rolling hills
- Realistic lighting with directional sunlight and shadows
- Checkerboard textured terrain for visual reference
- Shadow mapping with PCF filtering for improved visual quality

### Rover Simulation
- Physics-based movement with terrain conformance
- Realistic wheel spinning based on movement
- Throttle-based control system (proportional acceleration)
- Instantaneous friction-based deceleration
- Four-wheel terrain contact maintenance

### Camera System
- **Follow Camera**: Orbital camera that follows the rover
  - Right-click + drag to orbit around the rover
  - Scroll wheel to zoom in/out
  - Default position behind and above the rover
- **POV Camera**: First-person view from the rover's front
  - Toggle with 'V' key
  - Mounted at rover's front for realistic perspective

### User Interface
- Real-time telemetry display in the top-left corner:
  - Position coordinates (X, Y, Z)
  - Heading angle in degrees
  - Speed in km/h
  - Current camera mode indicator
- Clean, minimal interface with drop-shadow text for readability

## Technical Implementation

### Core Components

#### Main Application (`main.py`)
- Panda3D ShowBase subclass
- Window management (1280×720 resolution)
- Lighting setup with ambient and directional lights
- Shadow mapping configuration
- Physics world initialization
- Scene graph construction
- Input event handling
- Main game loop

#### Terrain System (`terrain.py`)
- Procedural heightmap generation using sine waves
- Visual mesh creation with vertex normals and colors
- Physics heightfield for collision detection
- Checkerboard texturing for movement reference
- Dual representation (visual and physics)

#### Rover System (`rover.py`)
- Rover body and wheel geometry generation
- Kinematic physics with terrain conformance
- Movement mechanics (throttle, steering)
- Wheel rotation simulation
- Terrain height sampling via raycasting
- Pitch and roll calculation for realistic orientation

#### Camera Controller (`camera.py`)
- Follow camera implementation with spherical coordinates
- POV camera with offscreen rendering buffer
- Mouse input handling for camera control
- Camera mode switching

#### Telemetry Display (`gui.py`)
- Onscreen text elements for telemetry data
- Real-time updates of position, heading, and speed
- Camera mode indication

### Controls

| Key | Action |
|-----|--------|
| ↑ | Throttle forward |
| ↓ | Throttle backward |
| ← | Steer left |
| → | Steer right |
| Right-click + drag | Orbit follow camera |
| Scroll wheel | Zoom follow camera in/out |
| V | Toggle follow/POV camera |
| Escape | Quit application |

### Physics and Movement

The rover uses a kinematic physics approach where:
- Movement is controlled directly through code
- Physics engine handles collision detection only
- Terrain conformance ensures all four wheels maintain contact
- Acceleration and deceleration follow realistic curves
- Steering affects heading directly without drift

### Rendering Pipeline

1. **Scene Setup**: Terrain and rover models are added to the scene graph
2. **Lighting**: Ambient and directional lights with shadow casting
3. **Shadows**: Custom GLSL shaders for PCF-filtered shadow mapping
4. **Cameras**: Active camera feeds the main display
5. **UI**: Telemetry overlay is rendered last

## Known Limitations (Phase 1)

- No networking or MQTT integration
- No suspension system (instant terrain conformance)
- Gentle terrain only (no large obstacles)
- Kinematic physics only (no dynamic interactions)
- POV buffer exists but no frame capture/streaming

## Future Enhancements (Planned for Phase 2)

- MQTT integration for telemetry publishing and control reception
- Configuration GUI for MQTT settings
- Persistent configuration storage
- Enhanced terrain with obstacles
- Suspension simulation for more realistic movement
- Video frame capture and streaming capabilities

## Dependencies

```
panda3d>=1.10
```

All required components (panda3d.bullet, direct GUI) are included with the standard Panda3D distribution.
