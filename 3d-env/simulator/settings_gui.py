"""
settings_gui.py - Native OS settings windows for Remote Rover simulator.

This replaces in-canvas ImGui dialogs with detached Tk windows so settings
can be moved/resized independently of the Panda3D render canvas.
"""

from __future__ import annotations

import copy
import json
import pathlib
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, ttk

from direct.showbase.DirectObject import DirectObject

from imgui_style import (
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    UI_FONT_CHOICES,
    UI_THEMES,
    normalize_ui_config,
)
from settings import load_settings, merge_settings, save_settings

_ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
_COMMON_LOCAL_PATH = _ROOT_DIR / "config" / "common.local.json"


class SettingsDialog(DirectObject):
    """Detached native settings windows (Tk)."""

    FIELD_WIDTH_CHARS = 52
    LABEL_MIN_WIDTH = 230
    SETTINGS_GEOMETRY = "1120x760"
    SETTINGS_MIN_SIZE = (860, 560)
    APPEARANCE_GEOMETRY = "860x420"
    APPEARANCE_MIN_SIZE = (700, 340)
    IMPORT_EXPORT_GEOMETRY = "840x280"
    IMPORT_EXPORT_MIN_SIZE = (700, 230)

    def __init__(self, cfg, on_apply, parent_simulator=None):
        DirectObject.__init__(self)
        self._cfg = copy.deepcopy(cfg)
        self._on_apply = on_apply
        self._sim = parent_simulator

        self._requested_tab = "mqtt"
        self._window_mode = "settings"
        self._status_text = ""
        self._default_path = _COMMON_LOCAL_PATH
        self._file_path = str(self._default_path)
        self._draft = {}

        self._root = None
        self._style = None
        self._windows = {}
        self._status_vars = {}
        self._vars = {}
        self._tk_pump_task_name = "settings-dialog-tk-pump"

        self._fill_draft_from_cfg(self._cfg)
        self._ensure_tk_runtime()

    def show(self):
        if self._window_mode == "appearance":
            self.switch_to_appearance()
        elif self._window_mode == "import_export":
            self.switch_to_import_export()
        else:
            self.switch_to_mqtt()

    def hide(self):
        for win in self._windows.values():
            if win.winfo_exists():
                win.withdraw()

    def toggle(self):
        if self.is_visible():
            self.hide()
        else:
            self.show()

    def is_visible(self):
        return any(win.winfo_exists() and win.state() != "withdrawn" for win in self._windows.values())

    def switch_to_mqtt(self):
        self._window_mode = "settings"
        self._requested_tab = "mqtt"
        self._show_settings_window("mqtt")

    def switch_to_keys(self):
        self._window_mode = "settings"
        self._requested_tab = "keys"
        self._show_settings_window("keys")

    def switch_to_import_export(self):
        self._window_mode = "import_export"
        self._show_import_export_window()

    def switch_to_appearance(self):
        self._window_mode = "appearance"
        self._show_appearance_window()

    def populate(self, cfg):
        self._cfg = copy.deepcopy(cfg)
        self._fill_draft_from_cfg(self._cfg)
        self._sync_vars_from_draft()
        self._apply_tk_fonts()
        self._set_status("")

    def _fill_draft_from_cfg(self, cfg):
        cfg = merge_settings(cfg, include_local=False)
        mqtt_cfg = cfg.get("mqtt", {})
        key_cfg = cfg.get("key_bindings", {})
        ui_cfg = normalize_ui_config(cfg.get("ui", {}))
        self._draft = {
            "theme": ui_cfg["theme"],
            "font_family": ui_cfg["font_family"],
            "font_size": ui_cfg["font_size"],
            "broker_host": mqtt_cfg["broker_host"],
            "broker_port": str(mqtt_cfg["broker_port"]),
            "topic_prefix": mqtt_cfg["topic_prefix"],
            "client_id": mqtt_cfg.get("client_id", ""),
            "control_topic": mqtt_cfg["control_topic"],
            "state_topic": mqtt_cfg["state_topic"],
            "camera_topic": mqtt_cfg["camera_topic"],
            "control_hz": str(mqtt_cfg["control_hz"]),
            "telemetry_hz": str(mqtt_cfg["telemetry_hz"]),
            "telemetry_policy": mqtt_cfg.get("telemetry_policy", "auto"),
            "gcs_presence_topic": mqtt_cfg.get("gcs_presence_topic", "gcs/presence"),
            "gcs_presence_timeout_ms": str(mqtt_cfg.get("gcs_presence_timeout_ms", 120000)),
            "failsafe_timeout_ms": str(mqtt_cfg["failsafe_timeout_ms"]),
            "control_mode": mqtt_cfg["control_mode"],
            "digital_throttle_step": str(mqtt_cfg["digital_throttle_step"]),
            "digital_steer_step": str(mqtt_cfg["digital_steer_step"]),
            "video_endpoint": mqtt_cfg["video_endpoint"],
            "battery_pct": str(mqtt_cfg["battery_pct"]),
            "voltage_v": str(mqtt_cfg["voltage_v"]),
            "current_a": str(mqtt_cfg["current_a"]),
            "temperature_c": str(mqtt_cfg["temperature_c"]),
            "forward": ", ".join(key_cfg["forward"]),
            "backward": ", ".join(key_cfg["backward"]),
            "left": ", ".join(key_cfg["left"]),
            "right": ", ".join(key_cfg["right"]),
            "camera_toggle": ", ".join(key_cfg["camera_toggle"]),
        }

    def _ensure_tk_runtime(self):
        if self._root is not None:
            return

        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("Remote Rover Settings Runtime")
        self._style = ttk.Style(self._root)

        if not getattr(base, "_settings_dialog_tk_pump_started", False):
            base.taskMgr.add(self._pump_tk, self._tk_pump_task_name, sort=100)
            base._settings_dialog_tk_pump_started = True

    def _pump_tk(self, task):
        if self._root is None:
            return task.cont
        try:
            self._root.update_idletasks()
            self._root.update()
        except tk.TclError:
            pass
        return task.cont

    def _create_window(self, key, title, geometry, min_size):
        win = self._windows.get(key)
        if win and win.winfo_exists():
            return win

        win = tk.Toplevel(self._root)
        win.title(title)
        win.geometry(geometry)
        win.minsize(min_size[0], min_size[1])
        win.resizable(True, True)
        win.protocol("WM_DELETE_WINDOW", win.withdraw)
        win.bind("<Escape>", lambda _event: win.withdraw())

        container = ttk.Frame(win, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)

        status_var = tk.StringVar(value="")
        self._status_vars[key] = status_var
        self._windows[key] = win
        return win

    def _create_scrolled_form(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        shell = ttk.Frame(parent)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=1)

        canvas = tk.Canvas(shell, borderwidth=0, highlightthickness=0)
        vscroll = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")

        content = ttk.Frame(canvas, padding=(2, 2, 2, 2))
        content.columnconfigure(0, minsize=self.LABEL_MIN_WIDTH)
        content.columnconfigure(1, weight=1)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def _on_content_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", _on_content_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        return content, canvas

    @staticmethod
    def _scroll_units_from_event(event):
        if getattr(event, "num", None) == 4:
            return -1
        if getattr(event, "num", None) == 5:
            return 1
        delta = getattr(event, "delta", 0)
        if delta > 0:
            return -1
        if delta < 0:
            return 1
        return 0

    def _bind_mouse_wheel(self, root_widget, canvas):
        def _on_wheel(event):
            units = self._scroll_units_from_event(event)
            if units:
                canvas.yview_scroll(units, "units")
                return "break"
            return None

        def _bind_recursive(widget):
            widget.bind("<MouseWheel>", _on_wheel, add="+")
            widget.bind("<Button-4>", _on_wheel, add="+")
            widget.bind("<Button-5>", _on_wheel, add="+")
            for child in widget.winfo_children():
                _bind_recursive(child)

        _bind_recursive(root_widget)

    def _show_settings_window(self, requested_tab):
        self._window_mode = "settings"
        self._requested_tab = requested_tab
        self._sync_vars_from_draft()

        win = self._create_window(
            "settings",
            "MQTT Setup",
            self.SETTINGS_GEOMETRY,
            self.SETTINGS_MIN_SIZE,
        )
        if not getattr(win, "_ui_built", False):
            self._build_settings_ui(win)
            win._ui_built = True

        notebook = getattr(win, "_settings_notebook", None)
        if notebook is not None:
            notebook.select(0 if requested_tab == "mqtt" else 1)

        win.deiconify()
        win.lift()
        win.focus_force()

    def _show_appearance_window(self):
        self._window_mode = "appearance"
        self._sync_vars_from_draft()

        win = self._create_window(
            "appearance",
            "Appearance",
            self.APPEARANCE_GEOMETRY,
            self.APPEARANCE_MIN_SIZE,
        )
        if not getattr(win, "_ui_built", False):
            self._build_appearance_ui(win)
            win._ui_built = True

        win.deiconify()
        win.lift()
        win.focus_force()

    def _show_import_export_window(self):
        self._window_mode = "import_export"
        self._sync_vars_from_draft()

        win = self._create_window(
            "import_export",
            "Import/Export",
            self.IMPORT_EXPORT_GEOMETRY,
            self.IMPORT_EXPORT_MIN_SIZE,
        )
        if not getattr(win, "_ui_built", False):
            self._build_import_export_ui(win)
            win._ui_built = True

        win.deiconify()
        win.lift()
        win.focus_force()

    def _new_var(self, key):
        var = tk.StringVar(value=str(self._draft.get(key, "")))
        self._vars[key] = var
        return var

    def _sync_vars_from_draft(self):
        for key, var in self._vars.items():
            if key in self._draft:
                var.set(str(self._draft[key]))
        if "file_path" in self._vars:
            self._vars["file_path"].set(self._file_path)

    def _push_vars_to_draft(self):
        for key, var in self._vars.items():
            value = var.get()
            if key == "file_path":
                self._file_path = value
            elif key in self._draft:
                self._draft[key] = value

    def _add_labeled_entry(self, parent, row, label, key, width=None):
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        entry = ttk.Entry(parent, textvariable=self._new_var(key), width=width or self.FIELD_WIDTH_CHARS)
        entry.grid(row=row, column=1, sticky="ew", pady=4)

    def _build_settings_ui(self, win):
        frame = win.winfo_children()[0]
        ttk.Label(frame, text="Configure broker settings and key bindings.").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        notebook = ttk.Notebook(frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky="nsew")
        frame.rowconfigure(1, weight=1)

        mqtt_tab = ttk.Frame(notebook, padding=10)
        keys_tab = ttk.Frame(notebook, padding=10)
        notebook.add(mqtt_tab, text="MQTT Broker")
        notebook.add(keys_tab, text="Key Bindings")
        win._settings_notebook = notebook

        mqtt_form, mqtt_canvas = self._create_scrolled_form(mqtt_tab)
        keys_form, keys_canvas = self._create_scrolled_form(keys_tab)

        mqtt_fields = [
            ("MQTT host", "broker_host"),
            ("MQTT port", "broker_port"),
            ("Topic prefix", "topic_prefix"),
            ("Client ID", "client_id"),
            ("Control topic", "control_topic"),
            ("State topic", "state_topic"),
            ("Camera topic", "camera_topic"),
            ("Control rate (Hz)", "control_hz"),
            ("Telemetry rate (Hz)", "telemetry_hz"),
            ("Telemetry policy", "telemetry_policy"),
            ("GCS presence topic", "gcs_presence_topic"),
            ("GCS presence timeout (ms)", "gcs_presence_timeout_ms"),
            ("Failsafe timeout (ms)", "failsafe_timeout_ms"),
            ("Control mode", "control_mode"),
            ("Digital throttle step", "digital_throttle_step"),
            ("Digital steer step", "digital_steer_step"),
            ("Video endpoint", "video_endpoint"),
            ("Battery (%)", "battery_pct"),
            ("Voltage (V)", "voltage_v"),
            ("Current (A)", "current_a"),
            ("Temperature (C)", "temperature_c"),
        ]
        for row, (label, key) in enumerate(mqtt_fields):
            self._add_labeled_entry(mqtt_form, row, label, key)

        tip = ttk.Label(
            mqtt_form,
            text="Leave Client ID blank for auto-generate. control_mode: hybrid|analog|digital. telemetry_policy: auto|force_on|force_off",
            wraplength=800,
            justify="left",
        )
        tip.grid(row=len(mqtt_fields), column=0, columnspan=2, sticky="w", pady=(8, 0))

        key_fields = [
            ("Forward", "forward"),
            ("Backward", "backward"),
            ("Left", "left"),
            ("Right", "right"),
            ("Camera toggle", "camera_toggle"),
        ]
        for row, (label, key) in enumerate(key_fields):
            self._add_labeled_entry(keys_form, row, label, key)

        ttk.Label(
            keys_form,
            text="Use Panda3D key names, comma-separated. Example: arrow_up, w",
            wraplength=800,
            justify="left",
        ).grid(row=len(key_fields), column=0, columnspan=2, sticky="w", pady=(8, 0))

        self._bind_mouse_wheel(mqtt_tab, mqtt_canvas)
        self._bind_mouse_wheel(keys_tab, keys_canvas)

        status = ttk.Label(frame, textvariable=self._status_vars["settings"], foreground="#225ea8")
        status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 2))

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Apply", width=12, command=self._on_apply_clicked).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", width=12, command=win.withdraw).pack(side="left", padx=4)

        self._apply_tk_fonts()

    def _build_appearance_ui(self, win):
        frame = win.winfo_children()[0]
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Choose the menu style and UI font.").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        ttk.Label(frame, text="Theme:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        theme_combo = ttk.Combobox(
            frame,
            state="readonly",
            values=list(UI_THEMES),
            textvariable=self._new_var("theme"),
            width=self.FIELD_WIDTH_CHARS,
        )
        theme_combo.grid(row=1, column=1, sticky="ew", pady=5)

        font_labels = [label for _, label in UI_FONT_CHOICES]
        font_key_to_label = dict(UI_FONT_CHOICES)
        font_label_to_key = {label: key for key, label in UI_FONT_CHOICES}
        chosen_label = font_key_to_label.get(self._draft.get("font_family", "default"), font_labels[0])

        ttk.Label(frame, text="Font:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)
        font_family_var = tk.StringVar(value=chosen_label)
        self._vars["font_family_label"] = font_family_var
        font_combo = ttk.Combobox(
            frame,
            state="readonly",
            values=font_labels,
            textvariable=font_family_var,
            width=self.FIELD_WIDTH_CHARS,
        )
        font_combo.grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Font size (px):").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=5)
        spin = ttk.Spinbox(
            frame,
            from_=int(MIN_FONT_SIZE),
            to=int(MAX_FONT_SIZE),
            textvariable=self._new_var("font_size"),
            width=8,
        )
        spin.grid(row=3, column=1, sticky="w", pady=5)

        def _sync_font_family(*_):
            label = font_family_var.get().strip()
            self._draft["font_family"] = font_label_to_key.get(label, "default")

        font_family_var.trace_add("write", _sync_font_family)

        ttk.Label(
            frame,
            text="Window font changes apply immediately after Apply.",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        status = ttk.Label(frame, textvariable=self._status_vars["appearance"], foreground="#225ea8")
        status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 2))

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Apply", width=12, command=self._on_apply_clicked).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", width=12, command=win.withdraw).pack(side="left", padx=4)

        self._apply_tk_fonts()

    def _build_import_export_ui(self, win):
        frame = win.winfo_children()[0]
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text="Import or export all settings as JSON.",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        path_frame = ttk.LabelFrame(frame, text="File", padding=10)
        path_frame.grid(row=1, column=0, sticky="ew")
        path_frame.columnconfigure(1, weight=1)

        ttk.Label(path_frame, text="File Path:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        file_var = self._new_var("file_path")
        file_var.set(self._file_path)
        entry = ttk.Entry(path_frame, textvariable=file_var, width=self.FIELD_WIDTH_CHARS)
        entry.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Button(path_frame, text="Browse", width=12, command=self._on_browse_file).grid(
            row=0, column=2, sticky="w", padx=(8, 0), pady=2
        )

        action_frame = ttk.LabelFrame(frame, text="Actions", padding=10)
        action_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for col in range(4):
            action_frame.columnconfigure(col, weight=1)
        ttk.Button(action_frame, text="Export JSON", command=self._on_export).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(action_frame, text="Import JSON", command=self._on_import).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(action_frame, text="Apply", command=self._on_apply_clicked).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(action_frame, text="Cancel", command=win.withdraw).grid(row=0, column=3, sticky="ew", padx=4)

        ttk.Label(
            frame,
            text="Tip: Import loads values into the form. Click Apply to activate and save.",
            foreground="#555555",
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))

        status = ttk.Label(frame, textvariable=self._status_vars["import_export"], foreground="#225ea8")
        status.grid(row=4, column=0, sticky="w", pady=(8, 2))

        self._apply_tk_fonts()

    def _set_status(self, text):
        self._status_text = text
        for var in self._status_vars.values():
            var.set(text)

    def _on_browse_file(self):
        self._push_vars_to_draft()
        path = filedialog.asksaveasfilename(
            title="Select settings file",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=pathlib.Path(self._file_path).name if self._file_path else "settings.json",
            initialdir=str(pathlib.Path(self._file_path).parent if self._file_path else self._default_path.parent),
        )
        if path:
            self._file_path = path
            if "file_path" in self._vars:
                self._vars["file_path"].set(path)

    def _collect(self):
        self._push_vars_to_draft()

        if "font_family_label" in self._vars:
            selected = self._vars["font_family_label"].get().strip()
            label_to_key = {label: key for key, label in UI_FONT_CHOICES}
            self._draft["font_family"] = label_to_key.get(selected, self._draft.get("font_family", "default"))

        port_text = self._draft["broker_port"].strip() or "61883"
        try:
            broker_port = int(port_text)
        except ValueError as exc:
            raise ValueError("MQTT port must be an integer.") from exc

        def _parse_int(key, label, minimum=1):
            raw = self._draft[key].strip()
            try:
                value = int(raw)
            except ValueError as exc:
                raise ValueError(f"{label} must be an integer.") from exc
            if value < minimum:
                raise ValueError(f"{label} must be >= {minimum}.")
            return value

        def _parse_float(key, label, minimum=0.0, maximum=None):
            raw = self._draft[key].strip()
            try:
                value = float(raw)
            except ValueError as exc:
                raise ValueError(f"{label} must be a number.") from exc
            if value < minimum:
                raise ValueError(f"{label} must be >= {minimum}.")
            if maximum is not None and value > maximum:
                raise ValueError(f"{label} must be <= {maximum}.")
            return value

        def _parse_keys(raw):
            return [key.strip() for key in raw.split(",") if key.strip()]

        cfg = copy.deepcopy(self._cfg)
        ui_cfg = normalize_ui_config(
            {
                "theme": self._draft["theme"],
                "font_family": self._draft["font_family"],
                "font_size": self._draft["font_size"],
            }
        )

        cfg["ui"] = {**cfg.get("ui", {}), **ui_cfg}
        cfg["mqtt"] = {
            **cfg.get("mqtt", {}),
            "broker_host": self._draft["broker_host"].strip(),
            "broker_port": broker_port,
            "topic_prefix": self._draft["topic_prefix"].strip(),
            "client_id": self._draft["client_id"].strip(),
            "control_topic": self._draft["control_topic"].strip(),
            "state_topic": self._draft["state_topic"].strip(),
            "camera_topic": self._draft["camera_topic"].strip(),
            "control_hz": _parse_int("control_hz", "Control rate (Hz)"),
            "telemetry_hz": _parse_int("telemetry_hz", "Telemetry rate (Hz)"),
            "telemetry_policy": self._draft["telemetry_policy"].strip().lower(),
            "gcs_presence_topic": self._draft["gcs_presence_topic"].strip(),
            "gcs_presence_timeout_ms": _parse_int("gcs_presence_timeout_ms", "GCS presence timeout (ms)"),
            "failsafe_timeout_ms": _parse_int("failsafe_timeout_ms", "Failsafe timeout (ms)"),
            "control_mode": self._draft["control_mode"].strip().lower(),
            "digital_throttle_step": _parse_float("digital_throttle_step", "Digital throttle step", 0.0, 1.0),
            "digital_steer_step": _parse_float("digital_steer_step", "Digital steer step", 0.0, 1.0),
            "video_endpoint": self._draft["video_endpoint"].strip(),
            "battery_pct": _parse_float("battery_pct", "Battery (%)", 0.0, 100.0),
            "voltage_v": _parse_float("voltage_v", "Voltage (V)", 0.0),
            "current_a": _parse_float("current_a", "Current (A)", 0.0),
            "temperature_c": _parse_float("temperature_c", "Temperature (C)", -273.15),
        }
        if cfg["mqtt"]["control_mode"] not in {"hybrid", "analog", "digital"}:
            raise ValueError("Control mode must be one of: hybrid, analog, digital.")
        if cfg["mqtt"]["telemetry_policy"] not in {"auto", "force_on", "force_off"}:
            raise ValueError("Telemetry policy must be one of: auto, force_on, force_off.")

        cfg["key_bindings"] = {
            **cfg.get("key_bindings", {}),
            "forward": _parse_keys(self._draft["forward"]),
            "backward": _parse_keys(self._draft["backward"]),
            "left": _parse_keys(self._draft["left"]),
            "right": _parse_keys(self._draft["right"]),
            "camera_toggle": _parse_keys(self._draft["camera_toggle"]),
        }
        return cfg

    def _resolve_path(self):
        raw_path = self._file_path.strip()
        if not raw_path:
            return self._default_path
        return pathlib.Path(raw_path)

    def _on_apply_clicked(self):
        try:
            new_cfg = self._collect()
        except ValueError as exc:
            self._set_status(str(exc))
            return

        current_ui = normalize_ui_config(self._cfg.get("ui", {}))
        new_ui = normalize_ui_config(new_cfg.get("ui", {}))
        font_changed = (
            current_ui["font_family"] != new_ui["font_family"]
            or current_ui["font_size"] != new_ui["font_size"]
        )

        self._cfg = copy.deepcopy(new_cfg)
        if self._on_apply:
            self._on_apply(new_cfg)

        self._apply_tk_fonts()
        self._set_status("Settings applied." if not font_changed else "Settings applied. Menu font may update on next launch.")

    def _on_export(self):
        try:
            export_cfg = self._collect()
        except ValueError as exc:
            self._set_status(str(exc))
            return

        path = self._resolve_path()
        if not path.parent.exists():
            self._set_status(f"Directory not found: {path.parent}")
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(export_cfg, fh, indent=2)
                fh.write("\n")
        except Exception as exc:
            self._set_status(f"Export failed: {exc}")
            return
        self._set_status(f"Exported to {path.name}")

    def _on_import(self):
        self._push_vars_to_draft()
        path = self._resolve_path()
        if not path.exists():
            self._set_status(f"File not found: {path}")
            return

        try:
            with open(path, encoding="utf-8") as fh:
                imported_cfg = json.load(fh)
        except Exception as exc:
            self._set_status(f"Import failed: {exc}")
            return
        self._fill_draft_from_cfg(imported_cfg)
        self._sync_vars_from_draft()
        self._apply_tk_fonts()
        self._set_status("Imported. Click Apply to activate.")

    def _pick_font_family(self, ui_cfg):
        family_choice = ui_cfg.get("font_family", "default")
        families = {name.lower(): name for name in tkfont.families(self._root)}
        wanted = {
            "readable": ["Atkinson Hyperlegible", "Noto Sans", "Segoe UI", "DejaVu Sans", "Arial", "Sans Serif"],
            "noto_sans": ["Noto Sans", "Segoe UI", "DejaVu Sans", "Arial", "Sans Serif"],
            "segoe_ui": ["Segoe UI", "Noto Sans", "DejaVu Sans", "Arial", "Sans Serif"],
            "dejavu_sans": ["DejaVu Sans", "Noto Sans", "Segoe UI", "Arial", "Sans Serif"],
            "default": [],
        }.get(family_choice, [])

        if not wanted:
            return None

        for candidate in wanted:
            found = families.get(candidate.lower())
            if found:
                return found
        return None

    def _apply_tk_fonts(self):
        if self._root is None:
            return

        ui_cfg = normalize_ui_config(self._cfg.get("ui", {}))
        pixel_size = -int(round(ui_cfg.get("font_size", 18.0)))
        pixel_size = min(-int(MIN_FONT_SIZE), max(-int(MAX_FONT_SIZE), pixel_size))
        family = self._pick_font_family(ui_cfg)

        for font_name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkMenuFont",
            "TkHeadingFont",
            "TkCaptionFont",
            "TkSmallCaptionFont",
            "TkIconFont",
            "TkTooltipFont",
            "TkFixedFont",
        ):
            try:
                f = tkfont.nametofont(font_name, root=self._root)
                config = {"size": pixel_size}
                if family:
                    config["family"] = family
                f.configure(**config)
            except tk.TclError:
                continue
