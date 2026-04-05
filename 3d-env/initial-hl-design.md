# Remote Rover 3D Environment — Initial High-Level Design

> Historical concept document.
> The project structure described in the original version is no longer current.
>
> Current structure:
> - simulator stays in `3d-env/`
> - GCS lives in `../gcs_server/`
> - shared runtime config currently lives in `simulator/settings.json`
>
> Use these current documents instead:
> - `../README.md`
> - `../GCS-web-app.md`
> - `../remote_rover_architecture_and_implementation_plan.md`
> - `mqtt-plan-canonical-2026-04-05_00-58-36.md`
> - `phase1-3D-Simulator.md`

## Historical Context

This file recorded the early concept stage when the project was still considering a combined simulator/server/frontend layout inside a single tree and a `config.json`-style settings flow.

Those assumptions are now outdated.

The main decisions that changed are:
- the GCS is now a separate application in `../gcs_server/`
- the current shared config source is `simulator/settings.json`
- there is no current `server/` + `frontend/` implementation under `3d-env/`
- the simulator MQTT implementation is now documented in `mqtt-plan-canonical-2026-04-05_00-58-36.md`

Keep this file only as historical design context.
