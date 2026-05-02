# Terrain Scene Manifest

## Purpose

The terrain scene manifest is the single source of truth for the current `3d-env` world geometry and map data.

Authoritative file:
- `config/terrain_scene.v1.json`

Validation file:
- `config/terrain_scene.schema.json`

Generator:
- `tools/generate_terrain_scene.py`

Validator:
- `tools/validate_terrain_scene.py`

## Current Model

The manifest is a text-based JSON file that contains the final expanded scene representation.

It explicitly defines:
- terrain size and heightfield samples
- terrain coordinate frame and artificial GPS georeference
- road centerlines and widths
- spawn points
- pads
- solar panels and frames
- building parts
- start-hub and charger parts
- rocks and boulders
- trees
- collision proxies and route-planning metadata where available

Runtime code should not invent object names, counts, coordinates, or dimensions. The simulator and GCS should read them from `terrain_scene.v1.json`.

## Virtual GPS

The scene uses local metric coordinates as the authoritative position model:
- `x`: east in meters
- `y`: north in meters
- `z`: altitude in meters

`coordinate_system.georeference` defines an artificial GPS anchor for compatibility with rover telemetry fields. The current conversion is a local tangent-plane approximation: moving one meter north in the simulator changes latitude by roughly one real meter, and moving one meter east changes longitude by roughly one real meter at the configured origin latitude.

This GPS is not read from the operator laptop or browser. It is deterministic mock GPS derived from the rover's virtual 3D position.

## Why JSON Is Used Here

JSON is used as the project source-of-truth format because both Python simulator code and JavaScript/browser-facing GCS code can consume it directly. It is also easy to validate and review in Git.

Future CAD/simulator exports can be generated from this manifest:
- `.usda` for NVIDIA Isaac Sim / OpenUSD workflows
- `.glb` or `.gltf` for simulation-ready visual meshes
- collision mesh files for physics
- STEP or other CAD references for authoritative engineering assets

The manifest remains the composition/index file even when individual objects later reference professional CAD-derived assets.

## Generate Or Regenerate

From the repository root:

```bash
cd /mnt/c/Users/vardana/Documents/Proj/remote-rover
python3 tools/generate_terrain_scene.py
```

This reads the legacy compact seed file:
- `config/terrain_scene.json`

and writes:
- `config/terrain_scene.v1.json`

The generator exists to preserve the current deterministic world while making the final object list explicit.

## Validate

From the repository root:

```bash
cd /mnt/c/Users/vardana/Documents/Proj/remote-rover
python3 tools/validate_terrain_scene.py
```

Expected result:

```text
terrain scene valid: .../config/terrain_scene.v1.json
```

## Runtime Consumers

Current runtime readers:
- `3d-env/simulator/terrain.py`
- `3d-env/simulator/main.py`
- `gcs_server/scene_map.py`

The simulator uses the manifest to build terrain, static scene geometry, spawn position, and obstacle/collider objects.

The GCS uses the same manifest for replay scene-map payloads and future route/map functionality.

## Editing Rule

For now, edit the compact generator input only when you intentionally want to regenerate the whole scene.

If the manifest is hand-edited, run the validator before using it. Long term, the compact seed file should either be removed or clearly archived after the expanded manifest becomes the only maintained source.
