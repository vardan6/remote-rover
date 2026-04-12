# Simulation Platform Plan — Review

**File reviewed:** `docs/simulation-platform-plan.md`
**Reviewed against version:** current implemented plan and current repository state
**Cross-check baseline:** `docs/simulation-platform-requironments.md`

---

## What Is Now Implemented

Compared with the earlier review state, these items are no longer only planned:

- backend identity is implemented in GCS config
- replay/session storage is implemented in GCS with SQLite
- replay APIs are implemented
- replay page is implemented
- first map playback is implemented on the replay page using Leaflet
- `rover-sim-next` exists as a repository scaffold

## What Improved Since the Previous Version

Many earlier issues were already addressed in this version:

- Recording/replay is now a first-class architecture requirement
- Headless mode is explicitly called out
- Isaac Sim properly framed as "explicit opt-in with hard NVIDIA dependency"
- ROS 2 no longer the hardwired default
- ENU-style local frame is mentioned
- Visual vs collision mesh separation and convex decomposition are mentioned
- SQLite for logging is a concrete, sensible choice
- The dev-asset vs authoritative-asset distinction is excellent architecture thinking

---

## Remaining Issues

This review is now focused on what is still missing relative to the requirements, not on items that are already implemented.

### 1. Live Map Is Still Not On The Main Dashboard

The replay page now has a first map implementation, but the main live dashboard still does not show a dedicated map.

Remaining work:
- add a live map panel
- reuse the same normalized track model as replay
- keep live and replay coordinate handling consistent

### 2. `rover-sim-next` Is Still A Scaffold

The successor simulator project now exists in the repository, but it is not yet a working backend.

Remaining work:
- implement the real ROS 2/Gazebo runtime
- implement the real MQTT bridge behavior
- implement rover/world loading
- implement headless/repeatable execution

### 3. Simulator-Side Logging Is Still Missing

The requirements call for logging on both the simulator side and the GCS side.
The GCS side is now implemented first, but simulator-side logging is still not present.

Remaining work:
- log locally produced telemetry/control/runtime events from the simulator side
- define how simulator-origin logs are imported or consumed in the GCS replay flow

### 4. Coordinate Model Is Still Only Partially Real

The system still depends on current pseudo-GPS compatibility values from `3d-env`.
Replay map support exists, but the full geospatial transform model is not yet implemented end-to-end.

### 5. CAD And Authoritative Asset Workflow Is Still Planned Only

The plan now names the workflow defaults, but there is still no implemented import or replacement path in code.

### 6. Video Recording And Synchronized Playback Are Still Future Work

The replay schema now reserves timing/media-reference support, but actual recorded video playback is still not implemented.

---

## Summary Table

| Area | Status |
|---|---|
| Recording/replay as first-class | Fixed |
| Headless mode | Fixed |
| Isaac Sim NVIDIA dependency | Fixed |
| ROS 2 not hardwired | Fixed |
| Requirements baseline document exists | Yes |
| Backend selection mechanism | Implemented in GCS |
| Replay/session storage | Implemented in GCS |
| Replay page | Implemented |
| First map playback | Implemented |
| Live dashboard map | Still missing |
| Simulator-side logging | Missing |
| `rover-sim-next` working backend | Missing |
| CAD/authoritative asset pipeline | Missing |
| Recorded video playback | Missing |
