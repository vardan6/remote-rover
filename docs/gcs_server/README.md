# GCS Server Documentation

## Purpose

`gcs_server/` is the browser-facing Ground Control Station for the Remote Rover project.

It is responsible for:
- serving the dashboard UI
- managing browser connections
- letting one browser control the rover at a time
- publishing MQTT control frames
- receiving telemetry and camera frames
- relaying telemetry and video to browsers
- publishing GCS presence so the simulator knows whether outbound data is currently needed

## What It Does Today

Implemented today:
- FastAPI backend
- browser dashboard
- WebSocket updates for telemetry, broker state, controller ownership, and video
- single-controller locking
- keyboard and on-screen browser controls
- MQTT control publication
- MQTT telemetry subscription
- MQTT camera-frame subscription
- MQTT setup page with live reconfiguration
- periodic and event-driven GCS presence publication

## Presence And Telemetry Enablement

One important current responsibility of the GCS is presence signaling.

The GCS publishes a retained presence record on:
- `{topic_prefix}/{gcs_presence_topic}/{gcs_id}`

Current behavior:
- presence is refreshed periodically
- presence is published immediately on browser connect/disconnect and controller changes
- presence is marked inactive on shutdown or disconnect through the MQTT last-will path
- simulator auto-publishing depends on these presence messages

This makes the GCS part of the simulator bandwidth-control loop.

## Browser Workflow

Current flow:
1. browser loads the dashboard
2. browser opens WebSocket to the GCS
3. browser receives the current runtime snapshot
4. browser may claim control
5. while controlling, browser sends held-button state changes
6. GCS publishes control frames to MQTT
7. telemetry and video received from MQTT are pushed back to all connected browsers

## Current Limitations

- state is still in memory only
- no authentication or authorization
- current video delivery is still the bootstrap WebSocket path fed from MQTT frames
- multi-instance GCS behavior is not yet fully hardened

## Main Files

- `app.py`: FastAPI routes and WebSocket endpoint
- `runtime.py`: service assembly and reconfiguration
- `mqtt_service.py`: MQTT connection, subscriptions, control publish, presence publish
- `control.py`: held-button control loop
- `state.py`: local runtime state and freshness tracking
- `ws.py`: WebSocket connection manager
- `static/`: dashboard and setup frontend assets

## How To Run

See the shared operations guide:
- [Run And Config Guide](../operations/run-and-config.md)

For deeper technical notes:
- [GCS Technical Details](./technical-details.md)
