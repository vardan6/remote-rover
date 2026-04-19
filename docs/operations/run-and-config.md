# Run And Config Guide

## Repository Layout

Repository root:
- `/mnt/c/Users/vardana/Documents/Proj/remote-rover`

Main subprojects:
- `3d-env/`
- `gcs_server/`
- `config/`
- `docs/`

## Shared Configuration

Shared runtime config files:
- `config/common.example.json`: tracked template
- `config/common.local.json`: local environment-specific override

Current shared config covers:
- MQTT broker host and port
- MQTT topic prefix and topic names
- control and telemetry rates
- telemetry publish policy
- GCS presence topic and timeout
- video mode defaults
- GCS host and port

Important rule:
- keep real environment-specific values only in `config/common.local.json`
- keep `common.example.json` safe for commit

## Current Important Shared Keys

### MQTT

- `mqtt.broker_host`
- `mqtt.broker_port`
- `mqtt.topic_prefix`
- `mqtt.client_id`
- `mqtt.control_topic`
- `mqtt.state_topic`
- `mqtt.camera_topic`
- `mqtt.control_hz`
- `mqtt.telemetry_hz`
- `mqtt.telemetry_policy`
- `mqtt.gcs_presence_topic`
- `mqtt.gcs_presence_timeout_ms`
- `mqtt.failsafe_timeout_ms`

### Video

- `video.enabled`
- `video.ingest_mode`
- `video.delivery_mode`

### GCS

- `gcs.host`
- `gcs.port`
- `gcs.telemetry_stale_ms`

## Running The Simulator

From `3d-env/` using Linux or WSL Python:

```bash
cd /mnt/c/Users/vardana/Documents/Proj/remote-rover/3d-env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python simulator/main.py
```

Helper launcher:

```bash
cd /mnt/c/Users/vardana/Documents/Proj/remote-rover/3d-env
./run.sh
```

Windows GPU launcher:

```powershell
cd C:\Users\vardana\Documents\Proj\remote-rover\3d-env
python -m venv .venv-gpu
.\.venv-gpu\Scripts\python -m pip install -r requirements.txt
.\run.bat
```

WSL bridge to the Windows GPU environment:

```bash
cd /mnt/c/Users/vardana/Documents/Proj/remote-rover/3d-env
./run_gpu.sh
```

WSL note:
- `run_gpu.sh` requires WSL interop to be enabled so the shell can invoke Windows executables
- if WSL interop is disabled, launch the simulator from Windows directly with `run.bat`

## Running The GCS

From the repository root:

```bash
cd /mnt/c/Users/vardana/Documents/Proj/remote-rover
pip install -r gcs_server/requirements-gcs.txt
python -m gcs_server
```

Open:
- `http://localhost:8080` by default

Alternative helper:

```bash
cd /mnt/c/Users/vardana/Documents/Proj/remote-rover/gcs_server
./run.sh
```

## Current Operational Sequence

For the current end-to-end demo flow:
1. make sure the MQTT broker is reachable
2. start the GCS
3. open the GCS in a browser
4. start the simulator
5. keep the GCS dashboard tab focused to drive
6. confirm telemetry and camera are visible

## Telemetry Publish Policy Operations

Current simulator policy options:
- `auto`
- `force_on`
- `force_off`

Meaning:
- `auto`: simulator publishes only while fresh GCS presence exists
- `force_on`: simulator always publishes outbound data
- `force_off`: simulator never publishes outbound data

Current places to control it:
- simulator menu: `Settings -> Telemetry Policy`
- simulator MQTT settings dialog
- shared config file under `mqtt.telemetry_policy`

Current auto-mode behavior:
- if no GCS browser is connected, the GCS presence becomes inactive or stale
- once no fresh active GCS remains, the simulator stops publishing telemetry and camera frames

## MQTT Setup Through The GCS

The GCS exposes a setup page:
- `/setup/mqtt`

Current behavior:
- reads current `mqtt.*` config
- allows broker/topic/control-rate editing
- writes back to shared config
- reconnects the GCS MQTT runtime without restarting the process

## Current Troubleshooting Notes

### Simulator Still Publishing In Auto Mode

Check:
- whether a retained active GCS presence is still fresh
- whether the simulator policy is set to `force_on`
- whether the GCS still has a connected browser session

Immediate stop option:
- set simulator telemetry policy to `force_off`

### WSL GPU Launcher Cannot Run Windows Python

Likely cause:
- WSL interop is disabled or unavailable in the current shell

Current workaround:
- run `run.bat` directly from Windows

### No Browser Video

Check:
- `video.enabled`
- `video.ingest_mode == mqtt_frames`
- `video.delivery_mode == websocket_mjpeg`
- broker connectivity
- whether simulator publish policy is currently allowing outbound data
