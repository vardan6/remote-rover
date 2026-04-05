> Deprecated: superseded for MQTT Phase 2 decisions by `mqtt-plan-canonical-2026-04-05_00-58-36.md`.
> Kept for historical context only.

# Remote Rover 3D Environment — High-Level Design (Qwen3 Version)

## Project Overview

The Remote Rover 3D Environment is a Python-based simulation platform designed to model a 3D virtual environment for an off-road rover vehicle. This simulator serves as a development and testing environment for a remote-controlled rover system, supporting the design and development of a web server that will eventually connect to a real rover.

## System Architecture

The complete system consists of three separate components connected via MQTT:

```
┌─────────────────────────────────────┐
│  Python 3D Rover Simulator          │  (Panda3D + panda3d.bullet)
│  - Desktop window + DirectGUI menus │
│  - Physics simulation               │
│  - POV camera capture               │
│  - Publishes telemetry + video      │
│  - Subscribes to control commands   │
└──────────────────┬──────────────────┘
                   │ MQTT (Mosquitto)
                   ▼
┌─────────────────────────────────────┐
│  Server (Python FastAPI)            │
│  - MQTT ↔ WebSocket relay           │
│  - Serves GCS web app               │
│  - Config / settings persistence    │
└──────────────────┬──────────────────┘
                   │ WebSocket / HTTP
                   ▼
┌─────────────────────────────────────┐
│  GCS Web App (browser)              │  ← multiple instances supported
│  - Displays POV video stream        │
│  - Telemetry dashboard              │
│  - Keyboard / peripheral controls   │
│  - Settings menu                    │
└─────────────────────────────────────┘
                   ▲
        Peripheral devices (joystick, etc.)
        can also send controls via MQTT
```

## Technology Stack

After evaluating various options, the chosen technology stack is:

**Primary Technologies:**
- **Panda3D** (v1.10.16+) - 3D rendering engine providing desktop window, terrain rendering, rover model, offscreen POV camera capture, and built-in GUI
- **panda3d.bullet** - Built-in Bullet physics module for realistic physics simulation
- **Python** - Primary programming language for all components

**Communication Layer:**
- **paho-mqtt** - MQTT connectivity for inter-component communication
- **FastAPI** - Web server framework for the server component
- **WebSocket** - Real-time communication between server and web clients

## Component Descriptions

### 3D Rover Simulator (Phase 1)
A standalone Python desktop application that:
- Renders a 3D environment with procedurally generated terrain
- Simulates rover physics with realistic terrain conformance
- Provides keyboard controls for movement (arrow keys)
- Features dual camera modes: orbital follow camera and first-person POV camera
- Displays real-time telemetry information (position, heading, speed)

### Server Component (Phase 3)
A Python FastAPI server that:
- Acts as a communication hub between the simulator and GCS clients
- Bridges MQTT and WebSocket protocols
- Serves the GCS web application
- Manages configuration persistence

### GCS Web Application (Phase 3)
A browser-based ground control station that:
- Displays the rover's POV video stream
- Shows real-time telemetry data
- Provides keyboard and peripheral device controls
- Offers a settings interface for configuration

## Development Phases

The implementation is divided into four phases:

**Phase 1 — 3D Simulator (Desktop, Standalone)**
- Basic 3D environment with terrain
- Rover model with physics
- Keyboard controls
- Camera system
- Telemetry display
- No networking

**Phase 2 — MQTT Integration**
- MQTT publishing of telemetry and video
- MQTT subscription to control commands
- Settings GUI for MQTT configuration
- Configuration persistence

**Phase 3 — Server + GCS Web App**
- FastAPI server implementation
- WebSocket communication
- GCS web application
- Full system integration

**Phase 4 — Multi-GCS + Peripherals**
- Support for multiple GCS instances
- Peripheral device integration
- Advanced features and extensibility

## Communication Protocol

The system uses MQTT for all communication with a hierarchical topic structure:

**Control Topics (Commands to Simulator):**
- `/remote-rover-01/controls/throttle` - Throttle control (0.0-1.0)
- `/remote-rover-01/controls/steering` - Steering control (-1.0-1.0)
- `/remote-rover-01/controls/brake` - Brake control (0.0-1.0)

**Telemetry Topics (Data from Simulator):**
- `/remote-rover-01/telemetry/position` - Position coordinates
- `/remote-rover-01/telemetry/heading` - Heading angle
- `/remote-rover-01/telemetry/imu` - IMU data (accelerometer, gyroscope)
- `/remote-rover-01/telemetry/gps` - GPS coordinates

**Video Topic:**
- `/remote-rover-01/video/pov` - JPEG-encoded POV video frames

All topics use a configurable prefix to support multiple rover instances.
