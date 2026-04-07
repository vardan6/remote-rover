import os
import sys
import time

# ── Environment detection (before Panda3D init) ────────────────────────────────
def _is_wsl():
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except (FileNotFoundError, OSError):
        return False

_WSL = _is_wsl()
_HAS_GPU_DEVICE = os.path.exists('/dev/dri/renderD128') if _WSL else True

from panda3d.core import load_prc_file_data

_prc = [
    "audio-library-name null",
    "evdev-no-udev 1",
    "want-directtools 0",
    # ── Performance ────────────────────────────────────────────────────────
    "sync-video true",           # VSync: GPU waits for display, no idle spinning
    "clock-mode limited",        # Cap frame rate instead of free-running
    "clock-frame-rate 60",       # Target 60 FPS
]
# Threaded rendering only benefits real GPUs — adds overhead on software renderer
if _HAS_GPU_DEVICE:
    _prc.append("threading-model Cull/Draw")

load_prc_file_data("", "\n".join(_prc))

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    Vec3, Point3, AmbientLight, DirectionalLight, LColor,
    WindowProperties, CardMaker, BitMask32, Texture, Shader, PNMImage, StringStream
)
from panda3d.bullet import BulletWorld, BulletRigidBodyNode, BulletSphereShape
from panda3d.core import (GeomNode, Geom, GeomTriangles, GeomVertexData,
                          GeomVertexFormat, GeomVertexWriter)
import math
import random

from terrain import Terrain, TERRAIN_SIZE
from rover import Rover
from camera import CameraController
from gui import TelemetryGUI, MenuBar, StatusBar, apply_imgui_theme
from imgui_style import normalize_ui_config
from settings import load_settings, save_settings
from settings_gui import SettingsDialog
from mqtt_bridge import MQTTBridge

VIDEO_PUBLISH_HZ = 10


# ── Rock mesh builder ─────────────────────────────────────────────────────────
def _clamp01(v):
    return max(0.0, min(1.0, v))


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _build_rock_node(name, rx, ry, rz, seed, base_col=(0.44, 0.40, 0.35), jitter=0.07):
    """Rough perturbed-sphere mesh for stone obstacles."""
    rng   = random.Random(seed)
    LATS  = 5
    LONS  = 8

    # Sphere vertices with random radial perturbation
    raw_verts = []
    for lat in range(LATS + 1):
        phi = math.pi * lat / LATS          # 0 (top) … π (bottom)
        for lon in range(LONS):
            theta = 2 * math.pi * lon / LONS
            p = 1.0 + rng.uniform(-0.22, 0.22)
            x = rx * p * math.sin(phi) * math.cos(theta)
            y = ry * p * math.sin(phi) * math.sin(theta)
            z = rz * p * math.cos(phi)
            raw_verts.append((x, y, z))

    fmt   = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")

    for (x, y, z) in raw_verts:
        vw.addData3(x, y, z)
        ln = math.sqrt(x * x + y * y + z * z) or 1e-6
        nw.addData3(x / ln, y / ln, z / ln)
        cw.addData4(
            _clamp01(base_col[0] + rng.uniform(-jitter, jitter)),
            _clamp01(base_col[1] + rng.uniform(-jitter, jitter)),
            _clamp01(base_col[2] + rng.uniform(-jitter, jitter)),
            1.0
        )

    tris = GeomTriangles(Geom.UHStatic)
    for lat in range(LATS):
        for lon in range(LONS):
            a  = lat * LONS + lon
            b  = lat * LONS + (lon + 1) % LONS
            c  = (lat + 1) * LONS + lon
            d  = (lat + 1) * LONS + (lon + 1) % LONS
            tris.addVertices(a, c, b)
            tris.addVertices(b, c, d)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode(name)
    gn.addGeom(geom)
    return gn


# ── Simulator ─────────────────────────────────────────────────────────────────
class RoverSimulator(ShowBase):
    def __init__(self):
        # Load settings first
        self._cfg = load_settings()
        self._mqtt_cfg = self._cfg.get("mqtt", {})
        self._last_video_pub_mono = 0.0

        ShowBase.__init__(self)

        self._software_mode = self._check_gpu()

        self._setup_window()
        self._setup_lighting()
        self._setup_physics()
        self._setup_scene()
        self._setup_controls()
        self._setup_gui()
        self._setup_mqtt()

        self.taskMgr.add(self._update, "update")
        if not self._software_mode:
            self.taskMgr.add(self._fix_shadow_border, "fix_shadow_border")

    # ------------------------------------------------------------------
    def _check_gpu(self):
        """Detect software rendering and print GPU diagnostics."""
        gsg = self.win.getGsg()
        renderer = gsg.getDriverRenderer()
        vendor = gsg.getDriverVendor()
        is_sw = 'llvmpipe' in renderer.lower() or 'swrast' in renderer.lower()

        tag = "SOFTWARE" if is_sw else "GPU"
        print(f"[{tag}] Renderer: {renderer}")
        print(f"[{tag}] Vendor:   {vendor}")

        if is_sw:
            print(f"[{tag}] *** Performance will be degraded — shadows disabled ***")
            if _WSL:
                print(f"[{tag}] WSL2 GPU passthrough not available.")
                print(f"[{tag}] For GPU rendering:")
                print(f"[{tag}]   ./run_gpu.sh        (from WSL)")
                print(f"[{tag}]   run.bat              (from Windows)")
                print(f"[{tag}] To fix WSLg GPU permanently:")
                print(f"[{tag}]   1. Update NVIDIA driver (nvidia.com/drivers)")
                print(f"[{tag}]   2. PowerShell (admin): wsl --update")
                print(f"[{tag}]   3. PowerShell: wsl --shutdown  (then reopen)")

        return is_sw

    # ------------------------------------------------------------------
    def _setup_window(self):
        props = WindowProperties()
        props.setTitle("Remote Rover Simulator")
        props.setSize(1280, 720)
        self.win.requestProperties(props)

    # Visual sun position — fixed in the sky for the glowing disc
    SUN_POS    = Point3(-70, -90, 130)
    _SUN_OFFSET = Vec3(-35, -45, 80)

    def _setup_lighting(self):
        ambient = AmbientLight("ambient")
        ambient.setColor(LColor(0.45, 0.47, 0.52, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor(LColor(1.05, 0.98, 0.85, 1))
        if not self._software_mode:
            sun.setShadowCaster(True, 2048, 2048)
            sun.getLens().setFilmSize(30, 30)
            sun.getLens().setNearFar(20, 180)

        self._sun_np = self.render.attachNewNode(sun)
        self._sun_np.setPos(self._SUN_OFFSET)
        self._sun_np.lookAt(Point3(0, 0, 0))
        self.render.setLight(self._sun_np)

        self._add_sun_disc(self.SUN_POS)
        self.render.setShaderAuto()

    def _add_sun_disc(self, pos):
        main_mask = self.cam.node().getCameraMask()
        cm = CardMaker("sun_disc")
        cm.setFrame(-1, 1, -1, 1)

        disc = self.render.attachNewNode(cm.generate())
        disc.setPos(pos); disc.setBillboardPointEye(); disc.setScale(6)
        disc.setColor(1.0, 0.97, 0.75, 1)
        disc.setLightOff(); disc.setShaderOff(); disc.setDepthWrite(False)
        disc.hide(BitMask32.allOn()); disc.show(main_mask)

        glow = self.render.attachNewNode(cm.generate())
        glow.setPos(pos); glow.setBillboardPointEye(); glow.setScale(14)
        glow.setColor(1.0, 0.90, 0.50, 0.18)
        glow.setLightOff(); glow.setShaderOff(); glow.setDepthWrite(False)
        glow.setTransparency(True)
        glow.hide(BitMask32.allOn()); glow.show(main_mask)

    def _setup_physics(self):
        self.bullet_world = BulletWorld()
        self.bullet_world.setGravity(Vec3(0, 0, -9.81))

    def _setup_scene(self):
        main_mask = self.cam.node().getCameraMask()

        self.terrain = Terrain(self.render, self.bullet_world)
        self.terrain.np.hide(BitMask32.allOn())
        self.terrain.np.show(main_mask)

        # Spawn high enough to let the suspension settle onto the terrain
        self.rover = Rover(self.render, self.bullet_world, start_pos=(0, 0, 4))

        # Obstacles and decor
        self._stone_nps = []
        self._tree_nps = []
        self._obstacle_footprints = []
        self._create_stones(main_mask)
        self._create_trees(main_mask)

        # PCF soft-shadow shader (GPU only — too expensive for software rendering)
        if not self._software_mode:
            pcf = Shader.load(Shader.SL_GLSL, "shadow_pcf.vert", "shadow_pcf.frag")
            self.terrain.np.setShader(pcf)
            self.rover.chassis_np.setShader(pcf)
            for wn in self.rover.wheel_nps:
                wn.setShader(pcf)
            for sn in self._stone_nps:
                sn.setShader(pcf)
            for tn in self._tree_nps:
                tn.setShader(pcf)

        self._flip_timer   = 0.0

        self.cam_ctrl = CameraController(self, self.rover)
        self.gui      = TelemetryGUI()

    # ── Stone obstacle creation ───────────────────────────────────────────────
    def _create_stones(self, main_mask):
        rng = random.Random(42)
        small_stones  = 18
        big_boulders  = 6
        total_stones  = small_stones + big_boulders
        placed = 0
        attempts = 0

        spawn_half_extent = TERRAIN_SIZE * 0.46
        spawn_clear_radius = 12.0

        while placed < total_stones and attempts < 800:
            attempts += 1
            # Random position on terrain, keep a clear zone around rover start
            px = rng.uniform(-spawn_half_extent, spawn_half_extent)
            py = rng.uniform(-spawn_half_extent, spawn_half_extent)
            if math.sqrt(px * px + py * py) < spawn_clear_radius:
                continue

            is_big = placed >= small_stones
            if is_big:
                radius = rng.uniform(0.90, 1.55)
                rx = radius * rng.uniform(0.90, 1.45)
                ry = radius * rng.uniform(0.90, 1.45)
                rz = radius * rng.uniform(0.65, 1.05)
            else:
                radius = rng.uniform(0.30, 0.72)
                rx = radius * rng.uniform(0.80, 1.30)
                ry = radius * rng.uniform(0.80, 1.30)
                rz = radius * rng.uniform(0.55, 0.90)

            # Keep obstacles from intersecting each other too heavily.
            footprint_radius = max(radius, rx, ry) * (1.18 if is_big else 1.05)
            if not self._is_obstacle_clear(px, py, footprint_radius):
                continue

            terrain_z = self.terrain.height_at(px, py)
            stone_z = terrain_z + rz * (0.55 if is_big else 0.60)

            # Physics: static sphere (mass=0)
            shape = BulletSphereShape(radius)
            tag = "boulder" if is_big else "stone"
            node = BulletRigidBodyNode(f"{tag}_{placed}")
            node.addShape(shape)
            node.setMass(0)
            stone_np = self.render.attachNewNode(node)
            stone_np.setPos(px, py, stone_z)
            stone_np.setHpr(
                rng.uniform(0, 360),
                rng.uniform(-15, 15),
                rng.uniform(-15, 15)
            )
            self.bullet_world.attachRigidBody(node)

            # Visual mesh
            if is_big:
                rock_color = (0.39, 0.36, 0.33)
                color_jitter = 0.09
            else:
                rock_color = (0.44, 0.40, 0.35)
                color_jitter = 0.07
            rock_gn = _build_rock_node(
                f"rock_{placed}",
                rx, ry, rz,
                seed=placed,
                base_col=rock_color,
                jitter=color_jitter,
            )
            rock_np = stone_np.attachNewNode(rock_gn)
            rock_np.setTwoSided(True)
            rock_np.hide(BitMask32.allOn())
            rock_np.show(main_mask)
            self._stone_nps.append(rock_np)
            self._obstacle_footprints.append((px, py, footprint_radius))

            placed += 1

    # ── Tree decoration ────────────────────────────────────────────────────────
    def _create_trees(self, main_mask):
        rng = random.Random(314)
        num_trees = 14
        placed = 0
        attempts = 0

        spawn_half_extent = TERRAIN_SIZE * 0.47
        spawn_clear_radius = 14.0

        while placed < num_trees and attempts < 900:
            attempts += 1
            px = rng.uniform(-spawn_half_extent, spawn_half_extent)
            py = rng.uniform(-spawn_half_extent, spawn_half_extent)
            if math.sqrt(px * px + py * py) < spawn_clear_radius:
                continue

            trunk_r = rng.uniform(0.16, 0.26)
            trunk_h = rng.uniform(1.1, 1.9)
            canopy_r = rng.uniform(0.85, 1.65)
            footprint_radius = max(trunk_r * 1.6, canopy_r * 0.55)

            if not self._is_obstacle_clear(px, py, footprint_radius):
                continue

            terrain_z = self.terrain.height_at(px, py)
            tree_np = self.render.attachNewNode(f"tree_{placed}")
            tree_np.setPos(px, py, terrain_z)
            tree_np.setHpr(
                rng.uniform(0, 360),
                rng.uniform(-3, 3),
                rng.uniform(-3, 3)
            )

            trunk_rx = trunk_r * rng.uniform(0.85, 1.18)
            trunk_ry = trunk_r * rng.uniform(0.85, 1.18)
            trunk_rz = trunk_h * 0.5
            trunk_gn = _build_rock_node(
                f"tree_trunk_{placed}",
                trunk_rx, trunk_ry, trunk_rz,
                seed=5000 + placed,
                base_col=(0.32, 0.23, 0.13),
                jitter=0.04,
            )
            trunk_np = tree_np.attachNewNode(trunk_gn)
            trunk_np.setZ(trunk_rz * 0.95)
            trunk_np.setTwoSided(True)

            canopy_rx = canopy_r * rng.uniform(0.80, 1.18)
            canopy_ry = canopy_r * rng.uniform(0.80, 1.18)
            canopy_rz = canopy_r * rng.uniform(0.72, 1.08)
            canopy_gn = _build_rock_node(
                f"tree_canopy_{placed}",
                canopy_rx, canopy_ry, canopy_rz,
                seed=7000 + placed,
                base_col=(0.19, 0.45, 0.17),
                jitter=0.06,
            )
            canopy_np = tree_np.attachNewNode(canopy_gn)
            canopy_np.setZ(trunk_h + canopy_rz * 0.22)
            canopy_np.setTwoSided(True)

            tree_np.hide(BitMask32.allOn())
            tree_np.show(main_mask)
            self._tree_nps.append(tree_np)
            self._obstacle_footprints.append((px, py, footprint_radius))
            placed += 1

    def _is_obstacle_clear(self, x, y, radius):
        for ox, oy, rr in self._obstacle_footprints:
            dx = x - ox
            dy = y - oy
            min_dist = radius + rr
            if dx * dx + dy * dy < min_dist * min_dist:
                return False
        return True

    def _reset_rover(self):
        """Teleport rover back to spawn with zeroed velocity (called after flip)."""
        cn = self.rover.chassis_np.node()
        self.rover.chassis_np.setPos(0, 0, 4)
        self.rover.chassis_np.setHpr(0, 0, 0)
        cn.setLinearVelocity(Vec3(0, 0, 0))
        cn.setAngularVelocity(Vec3(0, 0, 0))
        self.rover.reset_drive_state()

    # ------------------------------------------------------------------
    def _setup_controls(self):
        # _bound_keys tracks {action: [key, ...]} for every direction action so
        # we can cleanly unbind them when settings change.
        self._bound_keys: dict[str, list[str]] = {}
        self._cam_toggle_keys: list[str] = []

        self.key_map = {}
        self._key_sources = {}
        now = time.monotonic()
        self._last_local_axis_ts = {"throttle": now, "steering": now}
        self._last_mqtt_axis_ts = {"throttle": 0.0, "steering": 0.0}
        self._mqtt_axes = {"throttle": 0.0, "steering": 0.0}
        self._mqtt_buttons = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "stop": False,
            "camera_toggle": False,
        }
        self._last_mqtt_buttons = dict(self._mqtt_buttons)
        self._last_state_pub_mono = 0.0

        # Apply bindings from loaded settings
        self._rebind_keys(self._cfg["key_bindings"])

        self.accept("escape", self.userExit)

    def _setup_gui(self):
        """Initialize menu, status bar, and settings dialog bindings."""
        self._cfg["ui"] = normalize_ui_config(self._cfg.get("ui", {}))
        base._imgui_theme = self._cfg["ui"]["theme"]
        base._imgui_ui_config = self._cfg["ui"]
        self._menu = MenuBar(
            on_restart=self._reset_rover,
            on_mqtt=self._open_settings_mqtt,
            on_keys=self._open_settings_keys,
            on_appearance=self._open_settings_appearance,
            on_import_export=self._open_settings_import_export,
        )
        self._status = StatusBar()
        self._settings_dlg = None

        self.accept("control-r", self._reset_rover)
        self.accept("control-shift-r", self._reset_rover)
        self.accept("shift-control-r", self._reset_rover)
        self.accept("control-m", self._open_settings_mqtt)
        self.accept("control-k", self._open_settings_keys)
        self.accept("mouse1", self._on_mouse_click)

        self._status.set_status("Simulator ready")
        mqtt_cfg = self._cfg.get("mqtt", {})
        self._status.set_mqtt_state(
            "disabled",
            mode=mqtt_cfg["control_mode"],
            control_hz=mqtt_cfg["control_hz"],
            telemetry_hz=mqtt_cfg["telemetry_hz"],
        )

    def _setup_mqtt(self):
        self._mqtt_bridge = MQTTBridge(self._cfg.get("mqtt", {}))
        self._mqtt_bridge.start()

    def _on_mouse_click(self):
        """Close any open dropdown menus."""
        if self._menu:
            self._menu.hide_all_dropdowns()

    def _rebind_keys(self, bindings: dict):
        """Clear all current direction + camera bindings and apply *bindings*."""
        # Unbind old direction keys
        for action, keys in self._bound_keys.items():
            for key in keys:
                self.ignore(key)
                self.ignore(f"{key}-up")
        self._bound_keys = {}

        # Unbind old camera toggle keys
        for key in self._cam_toggle_keys:
            self.ignore(key)
        self._cam_toggle_keys = []

        # Reset key_map for drive directions
        drive_actions = [a for a in bindings if a != "camera_toggle"]
        self.key_map = {a: False for a in drive_actions}
        self._key_sources = {a: set() for a in drive_actions}

        for action, keys in bindings.items():
            if action == "camera_toggle":
                for key in keys:
                    self.accept(key, self._toggle_camera_if_ui_free)
                self._cam_toggle_keys = list(keys)
            else:
                for key in keys:
                    self._bind_direction_key(action, key, key)
                self._bound_keys[action] = list(keys)

    def _open_settings_mqtt(self):
        """Open settings dialog on MQTT tab."""
        if not self._settings_dlg:
            self._settings_dlg = SettingsDialog(
                self._cfg,
                on_apply=self._apply_settings,
                parent_simulator=self,
            )
        self._settings_dlg.switch_to_mqtt()

    def _open_settings_keys(self):
        """Open settings dialog on Key Bindings tab."""
        if not self._settings_dlg:
            self._settings_dlg = SettingsDialog(
                self._cfg,
                on_apply=self._apply_settings,
                parent_simulator=self,
            )
        self._settings_dlg.switch_to_keys()

    def _open_settings_import_export(self):
        """Open settings dialog on Import/Export tab."""
        if not self._settings_dlg:
            self._settings_dlg = SettingsDialog(
                self._cfg,
                on_apply=self._apply_settings,
                parent_simulator=self,
            )
        self._settings_dlg.switch_to_import_export()

    def _open_settings_appearance(self):
        """Open settings dialog on Appearance window."""
        if not self._settings_dlg:
            self._settings_dlg = SettingsDialog(
                self._cfg,
                on_apply=self._apply_settings,
                parent_simulator=self,
            )
        self._settings_dlg.switch_to_appearance()

    def _apply_settings(self, new_cfg):
        """Apply new settings from the dialog."""
        new_cfg["ui"] = normalize_ui_config(new_cfg.get("ui", {}))
        self._cfg = new_cfg
        self._mqtt_cfg = self._cfg.get("mqtt", {})
        base._imgui_ui_config = self._cfg["ui"]
        save_settings(new_cfg)
        apply_imgui_theme(new_cfg.get("ui", {}).get("theme", "light"))
        self._rebind_keys(new_cfg["key_bindings"])
        if hasattr(self, "_mqtt_bridge"):
            self._mqtt_bridge.stop()
        self._mqtt_bridge = MQTTBridge(self._cfg.get("mqtt", {}))
        self._mqtt_bridge.start()
        self._status.set_status("Settings applied")
        mqtt_cfg = self._cfg.get("mqtt", {})
        self._status.set_mqtt_state(
            self._mqtt_bridge.status_text(),
            mode=mqtt_cfg["control_mode"],
            control_hz=mqtt_cfg["control_hz"],
            telemetry_hz=mqtt_cfg["telemetry_hz"],
        )

    def _bind_direction_key(self, direction, event_name, source_id):
        self.accept(event_name,      self._set_key_source, [direction, source_id, True])
        self.accept(f"{event_name}-up", self._set_key_source, [direction, source_id, False])

    def _ui_keyboard_captured(self):
        imgui_backend = getattr(base, "imgui", None)
        return bool(imgui_backend and imgui_backend.isKeyboardCaptured())

    def _set_key_source(self, direction, source_id, is_down):
        if is_down and self._ui_keyboard_captured():
            return
        src = self._key_sources[direction]
        if is_down:
            src.add(source_id)
        else:
            src.discard(source_id)
        self.key_map[direction] = bool(src)
        now = time.monotonic()
        if direction in {"forward", "backward"}:
            self._last_local_axis_ts["throttle"] = now
        elif direction in {"left", "right"}:
            self._last_local_axis_ts["steering"] = now

    def _toggle_camera_if_ui_free(self):
        if self._ui_keyboard_captured():
            return
        self.cam_ctrl.toggle()

    def userExit(self):
        if hasattr(self, "_mqtt_bridge"):
            self._mqtt_bridge.stop()
        super().userExit()

    def _parse_mqtt_control(self, frame):
        if not isinstance(frame, dict):
            return

        mode = str(frame.get("mode", "hybrid")).lower()
        control_mode = str(self._cfg["mqtt"]["control_mode"]).lower()
        if control_mode in {"analog", "digital"}:
            mode = control_mode

        now = time.monotonic()
        buttons = frame.get("buttons", {})
        if not isinstance(buttons, dict):
            buttons = {}
        for name in self._mqtt_buttons:
            new_value = bool(buttons.get(name, self._mqtt_buttons[name]))
            self._mqtt_buttons[name] = new_value

        # Rising edge camera toggle command.
        if self._mqtt_buttons["camera_toggle"] and not self._last_mqtt_buttons["camera_toggle"]:
            self.cam_ctrl.toggle()
        self._last_mqtt_buttons = dict(self._mqtt_buttons)

        if mode in {"analog", "hybrid"}:
            if "throttle" in frame:
                try:
                    self._mqtt_axes["throttle"] = _clamp(float(frame.get("throttle", 0.0)), -1.0, 1.0)
                    self._last_mqtt_axis_ts["throttle"] = now
                except (TypeError, ValueError):
                    pass
            if "steering" in frame:
                try:
                    self._mqtt_axes["steering"] = _clamp(float(frame.get("steering", 0.0)), -1.0, 1.0)
                    self._last_mqtt_axis_ts["steering"] = now
                except (TypeError, ValueError):
                    pass

        if mode in {"digital", "hybrid"}:
            throttle_step = float(self._cfg["mqtt"]["digital_throttle_step"])
            steer_step = float(self._cfg["mqtt"]["digital_steer_step"])

            throttle = 0.0
            if self._mqtt_buttons["forward"]:
                throttle = throttle_step
            elif self._mqtt_buttons["backward"]:
                throttle = -throttle_step
            if self._mqtt_buttons["stop"]:
                throttle = 0.0

            steering = 0.0
            if self._mqtt_buttons["left"]:
                steering = steer_step
            elif self._mqtt_buttons["right"]:
                steering = -steer_step
            if self._mqtt_buttons["stop"]:
                steering = 0.0

            self._mqtt_axes["throttle"] = _clamp(throttle, -1.0, 1.0)
            self._mqtt_axes["steering"] = _clamp(steering, -1.0, 1.0)
            self._last_mqtt_axis_ts["throttle"] = now
            self._last_mqtt_axis_ts["steering"] = now

    def _collect_state_payload(self):
        pos = self.rover.pos
        heading = self.rover.heading
        speed_m_s = self.rover.speed / 3.6
        hpr = self.rover.chassis_np.getHpr(self.render)
        q = self.rover.chassis_np.getQuat(self.render)
        fwd = q.xform(Vec3(0, 1, 0))
        up = q.xform(Vec3(0, 0, 1))

        node = self.rover.chassis_np.node()
        if hasattr(node, "getLinearVelocity"):
            linear_v = node.getLinearVelocity()
            angular_v = node.getAngularVelocity()
        else:
            linear_v = node.get_linear_velocity()
            angular_v = node.get_angular_velocity()

        # Simple local-map projection from world meters to pseudo GPS degrees.
        base_lat = 40.1700
        base_lon = 44.5000
        lat = base_lat + (pos.y / 111320.0)
        lon = base_lon + (pos.x / (111320.0 * max(0.1, math.cos(math.radians(base_lat)))))

        mqtt_cfg = self._cfg.get("mqtt", {})
        return {
            "timestamp": time.time(),
            "position": {"x": pos.x, "y": pos.y, "z": pos.z},
            "gps": {"lat": lat, "lon": lon, "alt": pos.z},
            "orientation": {
                "heading_deg": heading,
                "hpr_deg": {"h": hpr.x, "p": hpr.y, "r": hpr.z},
                "forward": {"x": fwd.x, "y": fwd.y, "z": fwd.z},
                "up": {"x": up.x, "y": up.y, "z": up.z},
            },
            "imu": {
                "accel": {"x": 0.0, "y": 0.0, "z": -9.81},
                "gyro": {"x": angular_v.x, "y": angular_v.y, "z": angular_v.z},
            },
            "barometer": {"altitude_m": pos.z},
            "speed": {"m_s": speed_m_s, "km_h": self.rover.speed},
            "velocity": {
                "linear_m_s": {"x": linear_v.x, "y": linear_v.y, "z": linear_v.z},
                "angular_rad_s": {"x": angular_v.x, "y": angular_v.y, "z": angular_v.z},
            },
            "camera": {
                "enabled": True,
                "mode": "pov" if self.cam_ctrl.pov_active else "follow",
                "video_endpoint": mqtt_cfg["video_endpoint"],
            },
            "power": {
                "battery_pct": float(mqtt_cfg["battery_pct"]),
                "voltage_v": float(mqtt_cfg["voltage_v"]),
                "current_a": float(mqtt_cfg["current_a"]),
                "temperature_c": float(mqtt_cfg["temperature_c"]),
            },
        }

    def _publish_state_if_due(self, now_mono, payload):
        hz = max(1, int(self._cfg["mqtt"]["telemetry_hz"]))
        period = 1.0 / hz
        if now_mono - self._last_state_pub_mono < period:
            return
        self._last_state_pub_mono = now_mono
        self._mqtt_bridge.publish_state(payload)

    def _publish_video_if_due(self, now_mono):
        video_cfg = self._cfg.get("video", {})
        if not video_cfg.get("enabled", True):
            return
        if str(video_cfg.get("ingest_mode", "mqtt_frames")) != "mqtt_frames":
            return

        period = 1.0 / VIDEO_PUBLISH_HZ
        if now_mono - self._last_video_pub_mono < period:
            return

        pov_buffer = self.cam_ctrl.pov_buffer
        if pov_buffer is None:
            return

        image = PNMImage()
        if not pov_buffer.getScreenshot(image):
            return

        stream = StringStream()
        if not image.write(stream, "frame.jpg"):
            return

        frame_bytes = bytes(stream.getData())
        if not frame_bytes:
            return

        self._last_video_pub_mono = now_mono
        self._mqtt_bridge.publish_camera_frame(frame_bytes)

    def _fix_shadow_border(self, task):
        buf = self._sun_np.node().getShadowBuffer(self.win.getGsg())
        if buf is None:
            return task.cont
        tex = buf.getTexture()
        tex.setWrapU(Texture.WMBorderColor)
        tex.setWrapV(Texture.WMBorderColor)
        tex.setBorderColor(LColor(1, 1, 1, 1))
        return task.done

    # ------------------------------------------------------------------
    def _update(self, task):
        dt = globalClock.getDt()
        now_mono = time.monotonic()

        local_throttle = 0.0
        if self.key_map["forward"]:
            local_throttle = 1.0
        elif self.key_map["backward"]:
            local_throttle = -1.0

        local_steering = 0.0
        if self.key_map["left"]:
            local_steering = 1.0
        elif self.key_map["right"]:
            local_steering = -1.0

        timeout_s = max(0.05, float(self._cfg["mqtt"]["failsafe_timeout_ms"]) / 1000.0)
        frame, _age = self._mqtt_bridge.get_control_frame(timeout_s)
        if frame is not None:
            self._parse_mqtt_control(frame)
        else:
            self._mqtt_axes["throttle"] = 0.0
            self._mqtt_axes["steering"] = 0.0

        if self._last_local_axis_ts["throttle"] >= self._last_mqtt_axis_ts["throttle"]:
            throttle = local_throttle
        else:
            throttle = self._mqtt_axes["throttle"]

        if self._last_local_axis_ts["steering"] >= self._last_mqtt_axis_ts["steering"]:
            steering = local_steering
        else:
            steering = self._mqtt_axes["steering"]

        self.rover.throttle = throttle
        self.rover.steering = steering

        # Apply forces BEFORE stepping physics so they take effect this frame
        self.rover.update(dt)
        self.bullet_world.doPhysics(dt, 4, 1.0 / 60.0)

        # Flip detection: rover up-vector Z < 0 means upside-down (past 90°)
        up = self.rover.chassis_np.getQuat(self.render).xform(Vec3(0, 0, 1))
        if up.z < 0.0:
            self._flip_timer += dt
            if self._flip_timer >= 2.0:
                self._reset_rover()
                self._flip_timer = 0.0
        else:
            self._flip_timer = 0.0

        # Keep shadow centred on rover every frame (GPU mode only)
        if not self._software_mode:
            rp = self.rover.pos
            self._sun_np.setPos(Point3(rp.x + self._SUN_OFFSET.x,
                                       rp.y + self._SUN_OFFSET.y,
                                       rp.z + self._SUN_OFFSET.z))
            self._sun_np.lookAt(Point3(rp.x, rp.y, rp.z))
        self.cam_ctrl.update()
        state_payload = self._collect_state_payload()
        self._publish_state_if_due(now_mono, state_payload)
        self._publish_video_if_due(now_mono)
        self.gui.update_from_state(state_payload)
        mqtt_cfg = self._cfg.get("mqtt", {})
        self._status.set_mqtt_state(
            self._mqtt_bridge.status_text(),
            mode=mqtt_cfg["control_mode"],
            control_hz=mqtt_cfg["control_hz"],
            telemetry_hz=mqtt_cfg["telemetry_hz"],
        )
        self._status.set_telemetry(self.rover.pos, self.rover.heading, self.rover.speed)
        return task.cont


if __name__ == "__main__":
    app = RoverSimulator()
    app.run()
