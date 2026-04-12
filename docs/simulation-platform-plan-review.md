# Simulation Platform Plan — Review

**File reviewed:** `docs/simulation-platform-plan.md`
**Reviewed against version:** current implemented plan, current repository state, and updated execution priority
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

## Review Conclusion

The plan is broadly correct against the requirements, but it previously gave too much near-term weight to logging/replay work compared with the actual immediate need: making `rover-sim-next` real and GCS-compatible.

The corrected plan direction is:
- keep the requirements baseline unchanged
- keep replay/logging as part of the architecture
- defer additional replay/logging implementation until `rover-sim-next` works with the existing GCS
- prioritize the simulator backend, control/telemetry contract, rover/world model, and coordinate foundations

That sequencing is consistent with the original requests because:
- the user explicitly wants a better simulator as the main next step
- the system must keep `3d-env` working during transition
- the new backend must work with the current `gcs_server`
- logging/replay is required, but it does not need to block the first usable simulator milestone

## What Improved Since The Previous Version

Many earlier issues were already addressed in this version:

- Recording/replay is now a first-class architecture requirement
- Headless mode is explicitly called out
- The new plan now separates architecture requirements from immediate implementation order
- ROS 2 + Gazebo is now clearly treated as the chosen successor direction already scaffolded in-repo
- ENU-style local frame is mentioned
- Visual vs collision mesh separation and convex decomposition are mentioned
- SQLite for logging is a concrete, sensible choice
- The dev-asset vs authoritative-asset distinction is excellent architecture thinking

---

## Remaining Issues

This review is now focused on what is still missing relative to the requirements, not on items that are already implemented.

### 1. `rover-sim-next` Is Still A Scaffold

This is the primary gap and should remain the main implementation target.

Remaining work:
- implement the real ROS 2/Gazebo runtime
- implement the real MQTT bridge behavior
- implement rover/world loading with a first working rover and first working world
- implement headless/repeatable execution

### 2. Coordinate Model Is Still Only Partially Real

The simulator replacement needs a clear coordinate basis early, even if full map UI work is deferred.

Remaining work:
- define site origin explicitly
- formalize local frame semantics
- keep pseudo-GPS only as a compatibility layer during transition
- ensure `rover-sim-next` telemetry carries enough information for later live/replay mapping

### 3. CAD And Authoritative Asset Workflow Is Still Planned Only

The plan names the workflow well, but there is still no implemented import or replacement path in code.
That is acceptable for the first simulator milestone, but the simulator must be structured so this can be added without redesign.

### 4. Live Map Is Still Not On The Main Dashboard

This still matters relative to the requirements, but it should stay behind the simulator backend work in execution priority.

### 5. Simulator-Side Logging Is Still Missing

This still matters relative to the requirements, but it can now be explicitly deferred until after `rover-sim-next` works.

### 6. Video Recording And Synchronized Playback Are Still Future Work

This remains valid future work and does not block the first `rover-sim-next` implementation milestone.

---

## Summary Table

| Area | Status |
|---|---|
| Recording/replay as first-class | Fixed |
| Headless mode | Planned correctly |
| ROS 2 + Gazebo direction | Chosen and scaffolded |
| Requirements baseline document exists | Yes |
| Backend selection mechanism | Implemented in GCS |
| Replay/session storage | Implemented in GCS |
| Replay page | Implemented |
| First map playback | Implemented |
| `rover-sim-next` working backend | Missing |
| Coordinate foundation for successor simulator | Still partial |
| Live dashboard map | Still missing |
| Simulator-side logging | Deferred until after working backend |
| CAD/authoritative asset pipeline | Missing |
| Recorded video playback | Missing |
