from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_RUNTIME_CONFIG: dict[str, Any] = {
    "simulation": {
        "backend": "rover-sim-next",
        "backend_version": "dev",
    },
    "mqtt": {
        "broker_host": "127.0.0.1",
        "broker_port": 1883,
        "topic_prefix": "/projects/remote-rover",
        "client_id": "rover-sim-next",
        "control_topic": "control/manual",
        "state_topic": "telemetry/state",
        "camera_topic": "camera-feed",
        "gcs_presence_topic": "gcs/presence",
        "telemetry_hz": 10,
    },
    "site": {
        "name": "default-site",
        "frame": "enu",
        "default_projection": "utm",
    },
    "world": {
        "path": "worlds/dev_flat.sdf",
    },
    "vehicle": {
        "spawn": {
            "x": 0.0,
            "y": 0.0,
            "z": 0.35,
            "yaw_deg": 0.0,
        },
    },
}


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(out.get(key), dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_runtime_config(path: str | Path) -> tuple[dict[str, Any], Path]:
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Expected top-level mapping in {config_path}")
    merged = _deep_merge(DEFAULT_RUNTIME_CONFIG, raw)
    return merged, config_path
