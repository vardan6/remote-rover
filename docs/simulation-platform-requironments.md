# Simulation Platform Requirements

## Purpose

This document captures the user requirements for the simulation-platform work.

It is intentionally separate from:
- `docs/simulation-platform-plan.md`
- `docs/simulation-platform-plan-review.md`

This file is the baseline requirements reference.
When reviewing or updating the plan, the plan should always be compared against this requirements document so important requests are not missed.

This requirements file should only be updated:
- when the user explicitly asks to change it
- when a real project need requires clarifying or correcting a requirement

## Scope

These requirements apply to the current `remote-rover` repository and the future simulator work beside the existing `3d-env` project.

The goal is to support:
- the current working prototype
- a better long-term simulator platform
- phased migration without breaking the existing Ground Control Station

## Core Product Requirements

### 1. Keep The Existing System Working During Transition

The existing `3d-env` simulator must keep working during the transition period.

The new simulator work must:
- run in parallel with `3d-env`
- work with the existing `gcs_server`
- allow the current `gcs_server` to continue operating until the new simulator is ready to replace `3d-env`

If needed, `gcs_server` may be updated, but compatibility with the current working system should be preserved during migration.

### 2. Create A New Simulator Sub-Project

A new simulator sub-project should be created under the `remote-rover` repository.

This new sub-project is intended to:
- improve the 3D environment
- improve physics quality
- improve rover/world interaction
- improve modularity and future maintainability
- eventually replace the current `3d-env`

The working name may change, but the current planning baseline is a parallel successor project.

### 3. Preserve And Extend GCS Compatibility

The new simulator must work with the existing `gcs_server` contract during the transition.

The simulator platform should preserve compatibility for:
- rover control
- telemetry flow
- camera/video integration
- map integration
- replay visualization in the GCS

The GCS should be able to support both:
- the current `3d-env`
- the new simulator backend

until the new backend fully replaces the old one.

## 3D Simulation Requirements

### 4. Better 3D Environment

The future simulator should provide a better 3D environment than the current Panda3D-based setup.

The intended improvements include:
- better terrain/world modeling
- better rover modeling
- better physics behavior
- better rover interaction with the environment
- support for more customizable simulation scenes

The simulator should remain practical for iterative development and not lose important simulation capabilities while becoming more customizable.

### 5. Strong Physics And Simulation Behavior

The simulator must preserve meaningful 3D simulation capability.

The platform should support:
- rover motion in a 3D world
- physics-based rover/world interaction
- configurable rover physical properties
- future improvement of realism as better assets and engineering data become available

Customizability must not come at the cost of losing physics or simulation usefulness.

### 6. Prompt-Driven Early Development

During early development, it must be possible to build the rover, environment, and related assets using prompt-driven development with Codex or similar tooling.

This includes:
- generating early rover geometry
- generating early environment geometry
- generating rough world objects
- iterating through prompts for fast development

This is explicitly acceptable for early development, even though the final project assets should later be replaced by professional CAD-driven assets.

### 7. AI-Generated Assets Are Temporary Development Assets

AI-generated or quickly generated assets are acceptable for development, but they are not the engineering source of truth.

They should be treated as:
- temporary development assets
- replaceable by professional assets later
- compatible with the same top-level simulator and GCS interfaces

## CAD And Engineering Asset Requirements

### 8. Support Professional CAD Assets Later

Eventually, CAD drawings and models will be produced by professionals and correspond to the real project.

The platform must support that future workflow.

It should be possible to:
- provide CAD drawings for objects whenever necessary
- maintain object-level CAD or 3D model files separately
- work on those assets separately from the top-level simulator world
- include those separately maintained objects in the top-level model later

### 9. Modular Asset Workflow

Each major rover or environment object should be manageable independently.

The simulator should support:
- separate asset ownership
- separate update/replacement of objects
- composition of separately maintained assets into one world
- replacement of rough assets with authoritative assets without redesigning the whole simulator

### 10. Development-To-Authoritative Replacement Path

The platform must support a clean path from:
- early rough or AI-generated assets
- to later professional CAD-derived assets

This replacement should not require breaking:
- the top-level simulator workflow
- the GCS workflow
- telemetry/replay behavior

## Map And Positioning Requirements

### 11. World Map In The GCS

The system must support a world or site map in the Ground Control Station.

The user must be able to:
- see rover movement on the map
- relate rover telemetry to position on the map
- use the map in live operation
- use the map in replay visualization

The map may begin as a practical 2D implementation, but map support is required and should be planned early.

### 12. Position Synchronization

The system must support synchronization between:
- rover motion in the simulator
- telemetry data
- map position in the GCS
- future replay visualization

The same logical position model should be usable for both live and replay use cases.

## Logging And Replay Requirements

### 13. Logging Is A First-Class Requirement

Logging is not optional and must be part of the platform design early.

The system should log:
- telemetry data
- control traffic
- runtime events
- other important information that passes through the system

Video recording may come later, but logging and replay architecture must be planned now so video can be added correctly later.

### 14. Logging On Both Rover Side And GCS Side

Logging must be possible in both:
- rover/simulator side
- GCS side

The system should allow capture from either origin and make that usable in replay.

### 15. Replay Visualization In The GCS

Replay visualization must be available from the GCS.

Replay should support:
- rover movement visualization
- map playback
- telemetry playback
- control/event playback
- synchronized interpretation of captured session data

Replay may be implemented on a separate page in the GCS or later integrated differently, but replay capability from the GCS is required.

### 16. Synchronized Replay Timeline

The replay architecture must support synchronization across:
- rover movement
- map position
- telemetry values
- control/event timeline
- future video recording

Even if video recording is added later, the architecture should be designed so synchronized replay is possible without redesigning the system.

### 17. Storage For Logging

The system needs a structured place to store logs.

The storage backend may evolve, but the requirements are:
- structured queryable storage
- session-based recording
- support for replay
- support for synchronization across multiple data types

SQLite is currently an acceptable first implementation choice.

## Platform Evolution Requirements

### 18. Customizable Simulation Environment

The new simulation platform should be more customizable than the current environment.

This includes:
- customizable rover assets
- customizable environment/world assets
- customizable project-specific scenes
- the ability to adapt the simulator to different rover projects

### 19. Do Not Lose Simulation Value While Improving Modularity

The system should become more modular and more asset-driven, but it must not lose:
- 3D physics usefulness
- rover interaction quality
- simulation environment capability
- practical operator workflow support

### 20. Support Progressive Replacement

The new simulator should be able to coexist with the current one during migration.

The transition should allow:
- phased implementation
- phased GCS updates
- phased asset replacement
- eventual full replacement of `3d-env`

without forcing an immediate all-at-once migration.

## Documentation Process Requirements

### 21. Plan Reviews Must Be Checked Against Requirements

Whenever `docs/simulation-platform-plan.md` is reviewed, corrected, or expanded, it should be checked against this requirements document.

The review process should ask:
- which requirements are already covered
- which requirements are only partially covered
- which requirements are still missing
- whether the plan introduced assumptions that are not actually required

### 22. Requirements And Plan Must Stay Separate

The requirements document and the plan document serve different purposes.

This file defines:
- what is required

The plan defines:
- how the project currently intends to satisfy those requirements

The plan may change more often.
The requirements should stay more stable and only change when asked or when clearly necessary.

## Current Planning Implications

Based on the current requests, the plan should continue to account for:
- a new simulator beside `3d-env`
- compatibility with `gcs_server`
- early prompt-driven asset development
- later professional CAD-driven replacement
- map support in the GCS
- logging on both simulator and GCS sides
- replay visualization in the GCS
- synchronized future video support
- gradual replacement rather than immediate cutover
