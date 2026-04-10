# Remote Rover 3D Environment — Initial High-Level Design

> Historical concept document.
> The project structure described in the original version is no longer current.
> Start with `../docs/README.md` for the current documentation set.
>
> Current structure:
> - simulator stays in `3d-env/`
> - GCS lives in `../gcs_server/`
> - shared runtime config lives in `../config/common.local.json` with `../config/common.example.json` as fallback
> - simulator UI-only settings live in `simulator/settings.json`
>
> Use these current documents instead:
> - `../README.md`
> - `../remote_rover_architecture_and_implementation_plan.md`
> - `../PROJECT_REVIEW_AND_CURRENT_STATE.md`
> - `../gcs_server/GCS-web-app.md`
> - `mqtt-plan-canonical-2026-04-05_00-58-36.md`
> - `phase1-3D-Simulator.md`

## Historical Context

This file recorded the early concept stage when the project was still considering a combined simulator/server/frontend layout inside a single tree and a `config.json`-style settings flow.

Those assumptions are now outdated.

The main decisions that changed are:
- the GCS is now a separate application in `../gcs_server/`
- the current shared runtime config source is `../config/common.local.json`
- there is no current `server/` + `frontend/` implementation under `3d-env/`
- the simulator MQTT implementation began from `mqtt-plan-canonical-2026-04-05_00-58-36.md` and has since advanced to include MQTT camera-frame publication

Keep this file only as historical design context.
