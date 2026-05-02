# Rover3DEnva -- Cloud Code Project Prompt

## Goal

Create a **Python-based 3D rover simulator** that:

-   Runs locally from **VS Code using Cloud Code CLI**
-   Uses **PyBullet** for 3D physics simulation
-   Allows **keyboard driving with arrow keys**
-   Supports **MQTT communication**
-   Can run with or without MQTT enabled
-   Uses a **web interface** for visualization/control
-   Subscribes to MQTT topics and moves the rover based on received
    tokens

The simulator acts as a **virtual rover test environment** before
connecting to a real rover.

------------------------------------------------------------------------

# System Architecture

Browser (web UI)

→ Python Server (FastAPI)

→ PyBullet Simulation Engine

→ Virtual Rover

MQTT Broker (optional)

→ Commands sent to simulator

------------------------------------------------------------------------

# Core Technologies

Python 3.11+

Libraries:

-   pybullet
-   fastapi
-   uvicorn
-   paho-mqtt
-   asyncio
-   websockets

Frontend:

-   simple HTML + JavaScript

------------------------------------------------------------------------

# Project Structure

    rover3denv/
    │
    ├── app/
    │   ├── main.py
    │   ├── simulator.py
    │   ├── mqtt_client.py
    │   ├── config.py
    │   └── controls.py
    │
    ├── web/
    │   ├── index.html
    │   └── controls.js
    │
    ├── assets/
    │   └── terrain/
    │
    ├── requirements.txt
    └── README.md

------------------------------------------------------------------------

# Features

## 1. 3D Physics Environment

Uses **PyBullet** to simulate:

-   gravity
-   wheel traction
-   collision
-   rover movement

Terrain:

-   default flat plane
-   optional rough terrain

Rover model:

    racecar/racecar.urdf

------------------------------------------------------------------------

# Keyboard Control

The rover must respond to keyboard arrows:

  Key     Action
  ------- ---------------
  ↑       Move Forward
  ↓       Move Backward
  ←       Turn Left
  →       Turn Right
  Space   Stop

Keyboard events come from the browser and are sent to the Python server.

------------------------------------------------------------------------

# MQTT Mode

MQTT support must be **optional** and enabled from configuration.

Example config:

    USE_MQTT = true
    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883

------------------------------------------------------------------------

# MQTT Topic Design

Each rover command corresponds to a topic.

Example topics:

    rover/control/forward
    rover/control/backward
    rover/control/left
    rover/control/right
    rover/control/stop

Message payload examples:

    1
    0
    true
    false

When a message is received:

-   the simulator updates rover velocity
-   rover moves accordingly

------------------------------------------------------------------------

# MQTT Telemetry Publishing

The simulator should also publish state:

Topics:

    rover/state/position
    rover/state/speed
    rover/state/orientation

Payload example:

    {
     "x": 1.2,
     "y": 0.5,
     "z": 0.0
    }

Publish rate:

    10 Hz

------------------------------------------------------------------------

# Simulator Logic

The simulator loop runs at:

    240 Hz physics

Core tasks:

1.  Step PyBullet simulation
2.  Process control commands
3.  Publish telemetry
4.  Update rover velocity

------------------------------------------------------------------------

# FastAPI Web Server

The server exposes:

    GET /
    Web interface

    POST /control/forward
    POST /control/backward
    POST /control/left
    POST /control/right
    POST /control/stop

The web UI sends commands using fetch API.

------------------------------------------------------------------------

# Web Interface

The web page must:

-   render a simple control panel
-   capture arrow key events
-   send commands to server

Example JavaScript:

    document.addEventListener("keydown", function(event) {

      if(event.key === "ArrowUp")
         sendCommand("forward")

      if(event.key === "ArrowDown")
         sendCommand("backward")

      if(event.key === "ArrowLeft")
         sendCommand("left")

      if(event.key === "ArrowRight")
         sendCommand("right")

    })

------------------------------------------------------------------------

# MQTT Subscriber Template

Example Python snippet:

    import paho.mqtt.client as mqtt

    def on_message(client, userdata, msg):

        topic = msg.topic
        payload = msg.payload.decode()

        if topic == "rover/control/forward":
            rover.forward()

        if topic == "rover/control/backward":
            rover.backward()

        if topic == "rover/control/left":
            rover.left()

        if topic == "rover/control/right":
            rover.right()

------------------------------------------------------------------------

# Configuration File

config.py example:

    USE_MQTT = True

    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883

    CONTROL_TOPICS = {
     "forward": "rover/control/forward",
     "backward": "rover/control/backward",
     "left": "rover/control/left",
     "right": "rover/control/right",
     "stop": "rover/control/stop"
    }

------------------------------------------------------------------------

# Running the Simulator

Install dependencies:

    pip install -r requirements.txt

Start the simulator:

    python app/main.py

Open browser:

    http://localhost:8000

------------------------------------------------------------------------

# Future Extensions

-   camera simulation
-   lidar sensor simulation
-   terrain generator
-   multi‑rover simulation
-   ROS2 bridge
-   real rover hardware bridge

------------------------------------------------------------------------

# Expected Result

After running:

-   A **3D rover appears in PyBullet**
-   You can **drive it using arrow keys**
-   The rover can also be controlled through **MQTT messages**
-   Rover state is published back to MQTT

This provides a **complete virtual rover development environment** for
testing rover software before deploying to real hardware.
