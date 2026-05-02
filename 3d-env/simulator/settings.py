"""
settings.py — Load/save simulator settings.

Simulator-local UI settings live in simulator/settings.json.
Shared runtime settings live in ../../config/common.local.json with
../../config/common.example.json as the tracked safe fallback.
"""

import copy
import json
import pathlib

DEFAULT_SETTINGS = {
    "ui": {
        "theme": "light",
        "font_family": "readable",
        "font_size": 18.0,
    },
}

_DEFAULT_PATH = pathlib.Path(__file__).parent / "settings.json"
_ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
_COMMON_LOCAL_PATH = _ROOT_DIR / "config" / "common.local.json"
_COMMON_EXAMPLE_PATH = _ROOT_DIR / "config" / "common.example.json"


def load_settings(path=None):
    """Load simulator UI settings plus shared runtime settings."""
    path = pathlib.Path(path) if path else _DEFAULT_PATH
    return merge_settings(_load_json(path))


def merge_settings(patch=None, include_local=True):
    """Merge a partial config over tracked defaults and optional local overrides."""
    cfg = copy.deepcopy(DEFAULT_SETTINGS)
    cfg = _deep_merge(cfg, _load_json(_COMMON_EXAMPLE_PATH))
    if include_local:
        cfg = _deep_merge(cfg, _load_json(_COMMON_LOCAL_PATH))
    cfg = _deep_merge(cfg, patch or {})
    return cfg


def save_settings(cfg, path=None):
    """Write simulator-local UI settings and shared runtime settings separately."""
    path = pathlib.Path(path) if path else _DEFAULT_PATH
    try:
        _write_json(path, {"ui": copy.deepcopy(cfg.get("ui", {}))})
        shared_payload = {
            "mqtt": copy.deepcopy(cfg.get("mqtt", {})),
            "key_bindings": copy.deepcopy(cfg.get("key_bindings", {})),
            "video": copy.deepcopy(cfg.get("video", {})),
            "gcs": copy.deepcopy(cfg.get("gcs", {})),
            "simulation": copy.deepcopy(cfg.get("simulation", {})),
            "logging": copy.deepcopy(cfg.get("logging", {})),
            "map": copy.deepcopy(cfg.get("map", {})),
        }
        _write_json(_COMMON_LOCAL_PATH, shared_payload)
        print(f"[Settings] Saved simulator settings to {path}")
        print(f"[Settings] Saved shared settings to {_COMMON_LOCAL_PATH}")
    except Exception as e:
        print(f"[Settings] Failed to save {path}: {e}")


def _deep_merge(base, patch):
    """Return a new dict: patch values override base; nested dicts are merged recursively."""
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _load_json(path):
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Settings] Failed to load {path}: {e}")
        return {}


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
