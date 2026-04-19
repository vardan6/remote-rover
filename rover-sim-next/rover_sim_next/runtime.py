from __future__ import annotations

from pathlib import Path
from typing import Any


def _resolve_relative_path(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()

    config_dir = config_path.parent
    package_share = config_dir.parent
    candidate_from_config = (config_dir / path).resolve()
    if candidate_from_config.exists():
        return candidate_from_config
    return (package_share / path).resolve()


def _float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def resolve_runtime_summary(
    cfg: dict[str, Any],
    config_path: Path,
    launch_overrides: dict[str, Any],
) -> dict[str, Any]:
    world_cfg = str((cfg.get("world") or {}).get("path") or "worlds/dev_flat.sdf")
    world_input = str(launch_overrides.get("world_path") or world_cfg)
    world_resolved = _resolve_relative_path(config_path, world_input)

    spawn_cfg = ((cfg.get("vehicle") or {}).get("spawn") or {})
    return {
        "config_path": str(config_path),
        "backend": str((cfg.get("simulation") or {}).get("backend") or "rover-sim-next"),
        "backend_version": str((cfg.get("simulation") or {}).get("backend_version") or "dev"),
        "world_path": str(world_resolved),
        "spawn": {
            "x": _float_or_default(launch_overrides.get("spawn_x"), _float_or_default(spawn_cfg.get("x"), 0.0)),
            "y": _float_or_default(launch_overrides.get("spawn_y"), _float_or_default(spawn_cfg.get("y"), 0.0)),
            "z": _float_or_default(launch_overrides.get("spawn_z"), _float_or_default(spawn_cfg.get("z"), 0.35)),
            "yaw_deg": _float_or_default(launch_overrides.get("spawn_yaw"), _float_or_default(spawn_cfg.get("yaw_deg"), 0.0)),
        },
        "mqtt": {
            "broker_host": str((cfg.get("mqtt") or {}).get("broker_host") or "127.0.0.1"),
            "broker_port": int((cfg.get("mqtt") or {}).get("broker_port") or 1883),
            "topic_prefix": str((cfg.get("mqtt") or {}).get("topic_prefix") or ""),
            "control_topic": str((cfg.get("mqtt") or {}).get("control_topic") or ""),
            "state_topic": str((cfg.get("mqtt") or {}).get("state_topic") or ""),
            "camera_topic": str((cfg.get("mqtt") or {}).get("camera_topic") or ""),
            "gcs_presence_topic": str((cfg.get("mqtt") or {}).get("gcs_presence_topic") or ""),
            "telemetry_hz": int((cfg.get("mqtt") or {}).get("telemetry_hz") or 10),
        },
    }
