"""
imgui_style.py — Shared Dear ImGui styling helpers.

Handles:
- theme selection
- stable cross-platform widget scaling
- optional readable UI font loading with fallback
"""

from __future__ import annotations

import copy
import os
from pathlib import Path

try:
    import p3dimgui
    from imgui_bundle import imgui
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Missing GUI dependency. Install project requirements in the active "
        "environment with: python -m pip install -r requirements.txt"
    ) from exc


UI_THEMES = ("light", "dark", "classic")
UI_FONT_CHOICES = (
    ("readable", "Readable Sans"),
    ("noto_sans", "Noto Sans"),
    ("segoe_ui", "Segoe UI"),
    ("dejavu_sans", "DejaVu Sans"),
    ("default", "ImGui Default"),
)
DEFAULT_FONT_FAMILY = "readable"
DEFAULT_FONT_SIZE = 18.0
MIN_FONT_SIZE = 14.0
MAX_FONT_SIZE = 24.0

_FONT_CANDIDATES = {
    "readable": (
        "/usr/share/fonts/truetype/atkinson-hyperlegible/AtkinsonHyperlegible-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/mnt/c/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ),
    "noto_sans": (
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ),
    "segoe_ui": (
        "C:/Windows/Fonts/segoeui.ttf",
        "/mnt/c/Windows/Fonts/segoeui.ttf",
    ),
    "dejavu_sans": (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ),
    "default": (),
}


def normalize_ui_config(ui_cfg):
    ui_cfg = copy.deepcopy(ui_cfg or {})
    theme_name = (ui_cfg.get("theme") or "light").lower()
    if theme_name not in UI_THEMES:
        theme_name = "light"

    font_family = (ui_cfg.get("font_family") or DEFAULT_FONT_FAMILY).lower()
    if font_family not in dict(UI_FONT_CHOICES):
        font_family = DEFAULT_FONT_FAMILY

    try:
        font_size = float(ui_cfg.get("font_size", DEFAULT_FONT_SIZE))
    except (TypeError, ValueError):
        font_size = DEFAULT_FONT_SIZE
    font_size = max(MIN_FONT_SIZE, min(font_size, MAX_FONT_SIZE))

    return {
        **ui_cfg,
        "theme": theme_name,
        "font_family": font_family,
        "font_size": font_size,
    }


def apply_imgui_theme(theme_name):
    theme_name = normalize_ui_config({"theme": theme_name})["theme"]

    if theme_name == "dark":
        imgui.style_colors_dark()
    elif theme_name == "classic":
        imgui.style_colors_classic()
    else:
        imgui.style_colors_light()

    base._imgui_theme = theme_name
    base._imgui_applied_theme = theme_name


def _get_ui_scale():
    """
    Keep menu sizing stable across Linux/Windows by default.
    Optional overrides:
    - REMOTE_ROVER_UI_SCALE
    - P3DIMGUI_UI_SCALE
    """
    for env_name in ("REMOTE_ROVER_UI_SCALE", "P3DIMGUI_UI_SCALE"):
        raw = os.environ.get(env_name)
        if not raw:
            continue
        try:
            return max(0.8, min(float(raw), 2.5))
        except (TypeError, ValueError):
            continue
    return 1.0


def _apply_imgui_scale():
    if getattr(base, "_imgui_scale_applied", False):
        return

    scale = _get_ui_scale()
    style = imgui.get_style()
    style.scale_all_sizes(scale)
    base._imgui_ui_scale = scale
    base._imgui_scale_applied = True


def _resolve_font_path(font_family):
    for raw_path in _FONT_CANDIDATES.get(font_family, ()):
        path = Path(raw_path)
        if path.exists():
            return path
    return None


def _font_label(font_family):
    labels = dict(UI_FONT_CHOICES)
    return labels.get(font_family, "ImGui Default")


def _apply_imgui_font_settings_now(ui_cfg):
    ui_cfg = normalize_ui_config(ui_cfg)
    scale = getattr(base, "_imgui_ui_scale", 1.0)
    signature = (ui_cfg["font_family"], ui_cfg["font_size"], scale)
    if getattr(base, "_imgui_font_signature", None) == signature:
        return

    io = imgui.get_io()
    atlas = io.fonts
    atlas.clear()
    atlas.add_font_default()
    default_font = atlas.fonts[0]

    font_path = _resolve_font_path(ui_cfg["font_family"])
    loaded_font = None
    loaded_label = "ImGui Default"

    if font_path is not None:
        try:
            loaded_font = atlas.add_font_from_file_ttf(
                filename=str(font_path),
                size_pixels=ui_cfg["font_size"] * scale,
            )
            loaded_label = _font_label(ui_cfg["font_family"])
        except Exception as exc:
            print(f"[UI] Failed to load font {font_path}: {exc}")

    io.font_default = loaded_font if loaded_font is not None else default_font
    if loaded_font is None:
        imgui.get_style().font_scale_main = scale
        if ui_cfg["font_family"] != "default":
            loaded_label = "ImGui Default (fallback)"
    else:
        imgui.get_style().font_scale_main = 1.0

    base._imgui_font_signature = signature
    base._imgui_font_status = {
        "requested_family": ui_cfg["font_family"],
        "loaded_label": loaded_label,
        "path": str(font_path) if font_path else "",
        "size": ui_cfg["font_size"],
    }


def ensure_imgui(theme_name=None, ui_cfg=None):
    normalized_ui = normalize_ui_config(ui_cfg)
    theme_name = normalized_ui["theme"] if theme_name is None else theme_name

    if not hasattr(base, "imgui"):
        p3dimgui.init(
            style=theme_name,
            wantPlaceManager=False,
            wantExplorerManager=False,
            wantTimeSliderManager=False,
        )
        base._imgui_applied_theme = theme_name
    elif getattr(base, "_imgui_applied_theme", None) != theme_name:
        apply_imgui_theme(theme_name)

    _apply_imgui_scale()
    base._imgui_ui_config = normalized_ui
    _apply_imgui_font_settings_now(normalized_ui)
