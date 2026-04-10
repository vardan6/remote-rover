# Project Overview

## Executive Summary

Remote Rover is a rover-control platform built around two working applications:
- a 3D rover simulator that behaves like a remote vehicle
- a browser-based Ground Control Station (GCS) that operators use to monitor and drive the rover

The system uses MQTT as its current integration backbone. The simulator publishes telemetry and camera frames, and the GCS publishes control commands from the browser.

In its current state, the project already demonstrates the full operator loop:
1. a browser connects to the GCS
2. the operator takes control
3. the GCS publishes control frames over MQTT
4. the simulator receives those control frames and drives the rover
5. the simulator publishes telemetry and camera frames back over MQTT
6. the GCS shows telemetry and video in the browser

## What The Project Is For

At a high level, this project is a foundation for a remote vehicle operations stack.

It is useful for:
- simulator-first control workflow development
- operator dashboard and control UX development
- validating MQTT-based system contracts before connecting to a real rover
- presenting a future architecture for remote supervision, video, telemetry, and operator control

## Main Parts Of The System

### 1. 3D Simulator

The simulator is a Panda3D desktop application with Bullet physics.

It provides:
- a driveable rover with keyboard and MQTT control input
- live vehicle telemetry generation
- a simulated rover camera
- a terrain map with roads, solar plants, and an operations building
- a settings UI for MQTT and simulator behavior

### 2. Ground Control Station (GCS)

The GCS is a FastAPI web application with a browser frontend.

It provides:
- a telemetry dashboard
- browser-based manual control
- controller ownership so only one browser drives at a time
- rover camera display in the browser
- MQTT broker health and topic freshness visibility
- MQTT setup and reconfiguration from the browser

### 3. Shared Runtime Configuration

Both applications read shared runtime settings from the repository-level `config/` directory.

This keeps both sides aligned on:
- broker host and port
- topic prefix and MQTT topics
- control and telemetry rates
- video mode settings
- GCS host and port

## Current Project Value

The project is already strong enough to present as a working integrated prototype.

Current demonstration value:
- end-to-end remote control is implemented
- end-to-end telemetry is implemented
- end-to-end camera transport is implemented through an MQTT bootstrap path
- simulator publishing can now be suppressed automatically when no GCS is active, which matters for bandwidth-sensitive environments
- the codebase is already split into clear applications rather than a single mixed prototype tree

## Current Technology Position

The project is not yet in a final production architecture.

The current implementation should be understood as:
- a working simulator and control platform
- a practical integration baseline
- a strong demonstration and development environment
- a staging point for future hardening, better media transport, authentication, and multi-instance state management

## What Is Already Working vs What Is Planned

Working now:
- simulator driving
- browser control through the GCS
- MQTT control bridge
- MQTT telemetry bridge
- MQTT camera-frame bridge
- shared configuration
- GCS presence publishing
- simulator-side telemetry gating based on active GCS presence

Still planned:
- production-grade video transport such as WebRTC
- distributed shared state for multi-instance GCS deployments
- authentication and authorization
- deployment hardening and operational tooling
- clearer multi-GCS coordination policy

## Recommended Reading Order

For a general audience:
1. [Current State](./current-state.md)
2. [Implementation Roadmap](./implementation-roadmap.md)
3. [Architecture](./architecture.md)

For technical readers:
1. [Architecture](./architecture.md)
2. [Run And Config Guide](./operations/run-and-config.md)
3. [3D Simulator Docs](./3d-env/README.md)
4. [GCS Server Docs](./gcs_server/README.md)
