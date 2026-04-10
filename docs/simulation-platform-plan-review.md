# Simulation Platform Plan — Review

**File reviewed:** `docs/simulation-platform-plan.md`
**Reviewed against version:** current (updated, parallel-successor plan with `rover-sim-next`)

---

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

### 1. Map Library Still Not Named

The plan says "add early map support" and "map playback" but never names a library. The decision should be made explicit:

- **Leaflet.js** — correct first choice: 2D tiles, rover dot, heading arrow, no WebGL required, trivial to integrate into the existing GCS browser UI
- **MapLibre GL JS** — upgrade when vector tiles or smooth animation are needed
- **CesiumJS** — only if 3D globe/terrain becomes a requirement

### 2. CAD Tooling Still Not Named

The plan refers to "real CAD source files" and "authoritative CAD-derived geometry" without naming a tool. For an open-source project the default should be stated:

- **FreeCAD 1.0** (Nov 2024) — stable, open source, no subscription, the correct default
- **OpenSCAD** — worth naming for parametric components, relevant since current rover geometry is procedural code
- Onshape, Fusion 360, and SolidWorks are valid if already in team use but should not be the implied default

### 3. Mesh Format Is Vague

`"preferred simulation-ready mesh interchange format"` is undefined. Name it:

- **glTF/GLB** — correct choice: good material support, compact, widely supported by Blender, Bullet, and Gazebo

### 4. Coordinate Transform Is Under-Specified

`"ENU-style local frame"` is good but incomplete. Add:

- **pyproj** as the transform library (Python bindings for PROJ)
- **UTM** as the projection default for field deployments — simple and well-understood
- **LTP (Local Tangent Plane)** as an alternative for high-accuracy small-area sites

### 5. Physics Engine for `rover-sim-next` Not Named

The plan intentionally avoids locking an engine, which is correct. But candidate options should be listed to prevent the decision from staying vague indefinitely:

- **MuJoCo** — best contact physics, Python-native, free, headless-capable, no ROS required
- **PyBullet standalone** — direct upgrade from current Bullet/Panda3D, minimal stack change
- **gz-sim (Gazebo Ionic)** — only if ROS 2 hardware integration becomes a concrete requirement

### 6. AI-Generated Assets — Physics Accuracy Risk Not Acknowledged

The plan allows Codex-generated rover geometry for early iteration. This is pragmatically correct, but should note:

- AI-generated visual meshes are fine for appearance
- AI-generated collision meshes need validation — incorrect mass/inertia properties will cause wrong physics behavior
- Suggested rule: use AI for visual mesh, manually define collision primitives (boxes, cylinders, spheres) for physics until authoritative assets arrive

### 7. Backend Selection Mechanism Not Described

The plan states "one active simulator backend at a time" and "backend identity must be explicit in config or runtime selection" but never defines how. This should be resolved in Phase 1:

- A config-file flag (e.g. `backend: rover-sim-next` vs `3d-env`)
- Or a runtime GCS UI toggle
- This mechanism must be defined before any parallel-running is attempted

### 8. Video Sync Architecture Has No Sketch

The plan says "reserve synchronization support for video now" and "reserve a video panel." This is correct future-proofing, but the session model should specify at minimum:

- `camera_frame_index` or `pts` (presentation timestamp) in the session schema
- A note that video will be stored as a separate file referenced by session ID
- Without this, "reserved" is too vague to implement correctly when video is added

---

## Summary Table

| Area | Status |
|---|---|
| Recording/replay as first-class | Fixed |
| Headless mode | Fixed |
| Isaac Sim NVIDIA dependency | Fixed |
| ROS 2 not hardwired | Fixed |
| ENU frame convention | Partially fixed — library and projection type still missing |
| Convex decomposition mentioned | Yes — but mesh format (glTF/GLB) still not named |
| Map library | Not named |
| CAD tooling | Not named |
| Physics engine candidates | Not listed |
| AI asset physics accuracy risk | Not acknowledged |
| Backend selection mechanism | Not described |
| Video sync session schema | Too vague |
