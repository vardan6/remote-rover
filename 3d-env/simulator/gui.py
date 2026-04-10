"""
gui.py — GUI components for Remote Rover simulator.

Contains:
- TelemetryGUI: On-screen telemetry overlay aligned to MQTT state schema
- MenuBar: Top menu bar rendered with panda3d-imgui
- StatusBar: Bottom status bar with messages and telemetry
"""

from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame, DirectLabel
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, Vec4

from imgui_bundle import imgui

from imgui_style import apply_imgui_theme, ensure_imgui

COLOR_BG = Vec4(0.08, 0.08, 0.10, 0.90)
COLOR_PANEL = Vec4(0.14, 0.14, 0.16, 1.0)
COLOR_TEXT = Vec4(0.83, 0.83, 0.83, 1.0)
COLOR_STATUS_BG = Vec4(0.03, 0.25, 0.40, 1.0)


class TelemetryGUI:
    """On-screen telemetry overlay showing the MQTT state payload data."""

    def __init__(self):
        common = dict(
            align=TextNode.ALeft,
            fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 0.8),
            scale=0.045,
            mayChange=True,
        )
        self._lines = [
            OnscreenText(pos=(0.55, 0.90), **common),
            OnscreenText(pos=(0.55, 0.84), **common),
            OnscreenText(pos=(0.55, 0.78), **common),
            OnscreenText(pos=(0.55, 0.72), **common),
            OnscreenText(pos=(0.55, 0.66), **common),
        ]

    def update_from_state(self, payload):
        pos = payload.get("position", {})
        gps = payload.get("gps", {})
        orientation = payload.get("orientation", {})
        speed = payload.get("speed", {})
        power = payload.get("power", {})
        camera = payload.get("camera", {})

        self._lines[0].setText(
            "position x:{:+06.2f} y:{:+06.2f} z:{:+05.2f}".format(
                float(pos.get("x", 0.0)),
                float(pos.get("y", 0.0)),
                float(pos.get("z", 0.0)),
            )
        )
        self._lines[1].setText(
            "speed {:.1f} km/h ({:.2f} m/s)  heading {:.1f} deg".format(
                float(speed.get("km_h", 0.0)),
                float(speed.get("m_s", 0.0)),
                float(orientation.get("heading_deg", 0.0)),
            )
        )
        self._lines[2].setText(
            "gps lat:{:.6f} lon:{:.6f} alt:{:.2f} m".format(
                float(gps.get("lat", 0.0)),
                float(gps.get("lon", 0.0)),
                float(gps.get("alt", 0.0)),
            )
        )
        self._lines[3].setText(
            "power batt:{:.0f}%  {:.2f}V  {:.1f}A  {:.1f}C".format(
                float(power.get("battery_pct", 0.0)),
                float(power.get("voltage_v", 0.0)),
                float(power.get("current_a", 0.0)),
                float(power.get("temperature_c", 0.0)),
            )
        )
        self._lines[4].setText(
            "camera mode:{}  endpoint:{}".format(
                camera.get("mode", "follow"),
                camera.get("video_endpoint", ""),
            )
        )

    def update(self, pos, heading, speed, pov_active):
        cam_mode = "pov" if pov_active else "follow"
        payload = {
            "position": {"x": pos.x, "y": pos.y, "z": pos.z},
            "gps": {"lat": 0.0, "lon": 0.0, "alt": pos.z},
            "orientation": {"heading_deg": heading},
            "speed": {"km_h": speed, "m_s": speed / 3.6},
            "power": {"battery_pct": 0.0, "voltage_v": 0.0, "current_a": 0.0, "temperature_c": 0.0},
            "camera": {"mode": cam_mode, "video_endpoint": ""},
        }
        self.update_from_state(payload)


class MenuBar(DirectObject):
    """
    Top menu bar with Dear ImGui menus.

    Provides File, Simulation, and Settings menus while reusing the existing
    simulator callbacks for all actions.
    """

    def __init__(
        self,
        on_restart,
        on_mqtt,
        on_keys,
        on_appearance,
        on_import_export,
        telemetry_policy_getter=None,
        on_telemetry_policy_change=None,
    ):
        DirectObject.__init__(self)
        ensure_imgui(
            theme_name=getattr(base, "_imgui_theme", "light"),
            ui_cfg=getattr(base, "_imgui_ui_config", {}),
        )

        self._on_restart = on_restart
        self._on_mqtt = on_mqtt
        self._on_keys = on_keys
        self._on_appearance = on_appearance
        self._on_import_export = on_import_export
        self._telemetry_policy_getter = telemetry_policy_getter
        self._on_telemetry_policy_change = on_telemetry_policy_change

        self.accept("imgui-new-frame", self._draw)

    def _draw(self):
        if not imgui.begin_main_menu_bar():
            return

        if imgui.begin_menu("File"):
            imgui.end_menu()

        if imgui.begin_menu("Simulation"):
            if imgui.menu_item_simple(
                "Restart simulation",
                "Ctrl+R / Ctrl+Shift+R",
            ):
                self._on_restart_click()
            imgui.end_menu()

        if imgui.begin_menu("Settings"):
            if imgui.menu_item_simple("MQTT Setup", "Ctrl+M"):
                self._on_mqtt_click()
            if imgui.begin_menu("Telemetry Policy"):
                current_policy = "auto"
                if self._telemetry_policy_getter:
                    current_policy = str(self._telemetry_policy_getter() or "auto").strip().lower()
                for label, value in (
                    ("Automatic", "auto"),
                    ("Force Enabled", "force_on"),
                    ("Force Disabled", "force_off"),
                ):
                    if imgui.menu_item(label, "", current_policy == value)[0]:
                        self._on_telemetry_policy_click(value)
                imgui.end_menu()
            if imgui.menu_item_simple("Appearance"):
                self._on_appearance_click()
            if imgui.menu_item_simple("Import/Export"):
                self._on_import_export_click()
            imgui.end_menu()

        imgui.end_main_menu_bar()

    def _on_restart_click(self):
        if self._on_restart:
            self._on_restart()

    def _on_mqtt_click(self):
        if self._on_mqtt:
            self._on_mqtt()

    def _on_import_export_click(self):
        if self._on_import_export:
            self._on_import_export()

    def _on_telemetry_policy_click(self, policy):
        if self._on_telemetry_policy_change:
            self._on_telemetry_policy_change(policy)

    def _on_appearance_click(self):
        if self._on_appearance:
            self._on_appearance()

    def hide_all_dropdowns(self):
        """Dear ImGui menus close themselves; kept for compatibility."""
        return None


class StatusBar:
    """
    Bottom status bar showing connection status and live telemetry.

    Displays:
    - Left: Status messages (e.g., "Simulator ready", "Settings applied")
    - Right: Position, heading, speed telemetry
    """

    def __init__(self):
        self._status_text = "Initializing..."
        self._mqtt_state = "disabled"
        self._mqtt_mode = "hybrid"
        self._control_hz = 20
        self._telemetry_hz = 2
        self._telemetry_policy = "auto"
        self._telemetry_enabled = False
        self._frame = DirectFrame(
            frameColor=COLOR_STATUS_BG,
            frameSize=(-1.6, 1.6, -0.04, 0.04),
            pos=(0, 0, -0.92),
            sortOrder=5,
        )

        self._mqtt_lbl = DirectLabel(
            parent=self._frame,
            text="",
            text_fg=Vec4(0.75, 0.75, 0.75, 1),
            text_scale=0.035,
            text_align=TextNode.ALeft,
            pos=(-1.52, 0, 0),
            relief=None,
        )

        self._status_lbl = DirectLabel(
            parent=self._frame,
            text="",
            text_fg=Vec4(1, 1, 1, 1),
            text_scale=0.035,
            text_align=TextNode.ALeft,
            pos=(-0.20, 0, 0),
            relief=None,
        )

        self._telem_lbl = DirectLabel(
            parent=self._frame,
            text="",
            text_fg=Vec4(1, 1, 1, 1),
            text_scale=0.04,
            text_align=TextNode.ARight,
            pos=(1.5, 0, 0),
            relief=None,
        )
        self._refresh_status_label()

    def set_status(self, text):
        self._status_text = text
        self._refresh_status_label()

    def set_mqtt_state(
        self,
        state,
        mode=None,
        control_hz=None,
        telemetry_hz=None,
        telemetry_policy=None,
        telemetry_enabled=None,
    ):
        self._mqtt_state = state
        if mode is not None:
            self._mqtt_mode = str(mode)
        if control_hz is not None:
            self._control_hz = int(control_hz)
        if telemetry_hz is not None:
            self._telemetry_hz = int(telemetry_hz)
        if telemetry_policy is not None:
            self._telemetry_policy = str(telemetry_policy)
        if telemetry_enabled is not None:
            self._telemetry_enabled = bool(telemetry_enabled)
        self._refresh_status_label()

    def _refresh_status_label(self):
        state_text = self._normalized_state(self._mqtt_state)
        telemetry_state = "on" if self._telemetry_enabled else "off"
        self._mqtt_lbl.setText(
            f"MQTT {state_text} | M:{self._mqtt_mode} | C:{self._control_hz}Hz T:{self._telemetry_hz}Hz | Tel:{self._telemetry_policy}/{telemetry_state}"
        )
        self._mqtt_lbl["text_fg"] = self._mqtt_state_color(state_text)
        self._status_lbl.setText(self._status_text)

    def _normalized_state(self, state_text):
        s = str(state_text or "").lower()
        if "connected" in s and "disconnected" not in s:
            return "connected"
        if "connecting" in s:
            return "connecting"
        if "reconnecting" in s:
            return "reconnecting"
        if "disconnected" in s:
            return "disconnected"
        if "unavailable" in s:
            return "unavailable"
        if "error" in s or "failed" in s:
            return "error"
        if "disabled" in s:
            return "disabled"
        return "unknown"

    def _mqtt_state_color(self, state_text):
        s = state_text.lower()
        if s in {"disconnected", "error"}:
            return Vec4(1.0, 0.42, 0.42, 1.0)
        if s == "connected":
            return Vec4(0.45, 1.0, 0.50, 1.0)
        if s in {"connecting", "reconnecting"}:
            return Vec4(1.0, 0.82, 0.35, 1.0)
        if s in {"unavailable", "disabled"}:
            return Vec4(0.75, 0.75, 0.75, 1.0)
        return Vec4(0.75, 0.75, 0.75, 1.0)

    def set_telemetry(self, pos, heading, speed):
        self._telem_lbl.setText(
            f"x {pos.x:+.1f}  y {pos.y:+.1f}  {heading:.0f} deg  {speed:.1f} km/h"
        )

    def clear(self):
        self._status_lbl.setText("")
