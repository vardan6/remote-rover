# Repository Status Before First Push

## Push Readiness Summary

The `remote-rover/` repository is structurally ready to be initialized, added, committed, and pushed.

Current tracked project shape on disk:
- `3d-env/` contains the simulator and simulator-specific planning/history docs
- `gcs_server/` contains the Ground Control Station code and GCS docs
- root-level docs capture the current architecture, review findings, and project status
- root `.gitignore` now excludes local editor/runtime noise

## Verified Good

- GCS and simulator are physically separated
- root repository layout matches the intended workspace layout
- simulator settings include shared GCS/video keys
- simulator settings UI exposes `camera_topic`
- simulator code compiles
- GCS code compiles
- current docs are aligned with the current repo layout

## Known Intentional Gaps

These are not documentation mistakes; they are current implementation gaps:

1. Simulator camera frame publishing is not implemented yet.
2. GCS state backend is still in-memory only.
3. Shared runtime settings still live in one common JSON file and may later need finer separation.
4. WebRTC media delivery is planned but not implemented.

## Files That Preserve Current Project Context

Primary docs to keep:
- `README.md`
- `PROJECT_REVIEW_AND_CURRENT_STATE.md`
- `remote_rover_architecture_and_implementation_plan.md`
- `gcs_server/README.md`
- `gcs_server/GCS-web-app.md`
- `3d-env/mqtt-plan-canonical-2026-04-05_00-58-36.md`
- `3d-env/phase1-3D-Simulator.md`
- `3d-env/initial-hl-design.md`

## Recommended First Commit Scope

Include:
- root `.gitignore`
- `3d-env/`
- `gcs_server/`
- `requirements-gcs.txt`
- root markdown docs

Exclude by ignore:
- `.obsidian/`
- `.codex`
- `config/common.local.json`
- local virtual environments
- `__pycache__`
- `imgui.ini`
- local Claude settings

## First Post-Push Priorities

1. Implement simulator camera frame publishing to `mqtt.camera_topic`.
2. Decide whether the shared config should stay as one file or be split into smaller domains later.
3. Add Redis-backed shared GCS state if multi-instance deployment becomes necessary.

## Sensitive Data Rule

Keep real broker values only in:
- `config/common.local.json`

Do not commit real IPs, ports, credentials, or machine-specific endpoints into:
- tracked config templates
- code defaults
- documentation
