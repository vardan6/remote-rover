"""Placeholder MQTT bridge for rover-sim-next.

This file intentionally does not implement the real ROS 2 + Gazebo bridge yet.
It exists so the new simulator backend has a concrete starting point in-repo.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    return {"raw_text": text, "path": str(path)}


def build_contract_summary(config: dict) -> str:
    return json.dumps(
        {
            "backend": "rover-sim-next",
            "contract_topics": [
                "control_topic",
                "state_topic",
                "camera_topic",
                "gcs_presence_topic",
            ],
            "config_path": config.get("path"),
        },
        indent=2,
    )


if __name__ == "__main__":
    cfg = load_config(Path(__file__).resolve().parent.parent / "config" / "rover_sim_next.example.yaml")
    print(build_contract_summary(cfg))
