import os
import sys
import time

from gpu_probe import (
    detect_startup_environment,
    format_preflight_lines,
    format_runtime_lines,
)

# ── Optimus hint DLL (must load before Panda3D touches the display pipe) ───────
# run.bat sets ROVER_OPTIMUS_HINT to the path of optimus_hint.dll when it exists.
# Loading this DLL causes the NVIDIA driver to see the NvOptimusEnablement=1
# export and route WGL (OpenGL) rendering to the discrete GPU.
_OPTIMUS_HINT = os.environ.get("ROVER_OPTIMUS_HINT", "")
if _OPTIMUS_HINT and os.path.isfile(_OPTIMUS_HINT):
    import ctypes
    try:
        ctypes.CDLL(_OPTIMUS_HINT)
        print(f"[GPU-PREFLIGHT] Optimus hint DLL loaded: {_OPTIMUS_HINT}")
    except OSError as _e:
        print(f"[GPU-PREFLIGHT] Failed to load optimus hint DLL: {_e}")

# ── Environment detection (before Panda3D init) ────────────────────────────────
_GPU_PREF = os.environ.get("ROVER_GPU_PREFERENCE", "nvidia")
_GPU_PREFLIGHT = detect_startup_environment(_GPU_PREF)
for _line in format_preflight_lines(_GPU_PREFLIGHT):
    print(_line)

_WSL = _GPU_PREFLIGHT["is_wsl"]
_HAS_GPU_DEVICE = _GPU_PREFLIGHT["threaded_rendering_supported"]

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
    WindowProperties, CardMaker, BitMask32, Texture, PNMImage, StringStream,
    DepthOffsetAttrib
)
from panda3d.bullet import BulletWorld, BulletRigidBodyNode, BulletSphereShape, BulletBoxShape
from panda3d.core import (GeomNode, Geom, GeomTriangles, GeomVertexData,
                          GeomVertexFormat, GeomVertexWriter)
import math
import random

from terrain import Terrain, SCENE_OBJECTS, SPAWN_POINTS, SCENE_GEOREFERENCE
from rover import Rover
from camera import CameraController
from gui import TelemetryGUI, MenuBar, StatusBar, apply_imgui_theme
from georeference import local_to_gps, normalize_georeference
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


def _build_box_node(name, hx, hy, hz, color):
    """Create a simple box mesh centered at origin."""
    fmt = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")

    # Each face uses 4 dedicated vertices so normals stay crisp.
    faces = [
        ((0, 0, 1), [(-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]),
        ((0, 0, -1), [(-hx, hy, -hz), (hx, hy, -hz), (hx, -hy, -hz), (-hx, -hy, -hz)]),
        ((1, 0, 0), [(hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz), (hx, -hy, hz)]),
        ((-1, 0, 0), [(-hx, hy, -hz), (-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz)]),
        ((0, 1, 0), [(-hx, hy, -hz), (hx, hy, -hz), (hx, hy, hz), (-hx, hy, hz)]),
        ((0, -1, 0), [(hx, -hy, -hz), (-hx, -hy, -hz), (-hx, -hy, hz), (hx, -hy, hz)]),
    ]

    tris = GeomTriangles(Geom.UHStatic)
    base_idx = 0
    for normal, verts in faces:
        for x, y, z in verts:
            vw.addData3(x, y, z)
            nw.addData3(*normal)
            cw.addData4(color[0], color[1], color[2], 1.0)
        tris.addVertices(base_idx, base_idx + 1, base_idx + 2)
        tris.addVertices(base_idx, base_idx + 2, base_idx + 3)
        base_idx += 4

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    return node


# ── Simulator ─────────────────────────────────────────────────────────────────
class RoverSimulator(ShowBase):
    def __init__(self):
        # Load settings first
        self._cfg = load_settings()
        self._mqtt_cfg = self._cfg.get("mqtt", {})
        self._georeference = normalize_georeference(SCENE_GEOREFERENCE)
        self._last_video_pub_mono = 0.0
        self._gpu_preference = _GPU_PREFLIGHT["preference"]

        ShowBase.__init__(self)

        self._force_shadows = os.environ.get("ROVER_FORCE_SHADOWS", "").lower() in ("1", "true", "yes", "on")
        self._software_mode = self._check_gpu()
        self._shadows_enabled = (not self._software_mode) or self._force_shadows

        self._setup_window()
        self._setup_lighting()
        self._setup_physics()
        self._setup_scene()
        self._setup_controls()
        self._setup_gui()
        self._setup_mqtt()

        self.taskMgr.add(self._update, "update")
        if self._shadows_enabled:
            self.taskMgr.add(self._fix_shadow_border, "fix_shadow_border")

    # ------------------------------------------------------------------
    def _check_gpu(self):
        """Detect software rendering and print GPU diagnostics."""
        gsg = self.win.getGsg()
        renderer = gsg.getDriverRenderer()
        vendor = gsg.getDriverVendor()
        runtime_lines, is_sw, runtime_class = format_runtime_lines(
            renderer,
            vendor,
            self._gpu_preference,
        )
        for line in runtime_lines:
            print(line)

        tag = "SOFTWARE" if is_sw else "GPU"
        if runtime_class == "nvidia":
            print(f"[{tag}] NVIDIA acceleration active.")
        elif runtime_class == "amd":
            print(f"[{tag}] AMD acceleration active.")
        elif runtime_class == "intel":
            print(f"[{tag}] Intel/native OpenGL acceleration active.")
        elif runtime_class == "unknown":
            print(f"[{tag}] GPU vendor not recognized; continuing with detected renderer.")

        if is_sw:
            if self._force_shadows:
                print(f"[{tag}] Software renderer detected, but ROVER_FORCE_SHADOWS is enabled.")
                print(f"[{tag}] Shadows will run with reduced performance.")
            else:
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
            else:
                print(f"[{tag}] Linux software renderer detected (likely llvmpipe/swrast).")
                print(f"[{tag}] Verify OpenGL driver install and active GPU renderer.")
                print(f"[{tag}] You can force shadows for testing: ROVER_FORCE_SHADOWS=1")

        return is_sw

    # ------------------------------------------------------------------
    def _setup_window(self):
        props = WindowProperties()
        props.setTitle("Remote Rover Simulator")
        props.setSize(1280, 720)
        self.win.requestProperties(props)
        self.setBackgroundColor(0.60, 0.73, 0.90, 1.0)

    # Visual sun position — fixed in the sky for the glowing disc
    SUN_POS    = Point3(-70, -90, 130)
    _SUN_OFFSET = Vec3(-35, -45, 80)

    def _setup_lighting(self):
        ambient = AmbientLight("ambient")
        ambient.setColor(LColor(0.45, 0.47, 0.52, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor(LColor(1.05, 0.98, 0.85, 1))
        if self._shadows_enabled:
            # Large fixed shadow frustum to avoid a moving shadow-camera footprint.
            sun.setShadowCaster(True, 4096, 4096)
            sun.getLens().setFilmSize(440, 440)
            sun.getLens().setNearFar(10, 520)

        self._sun_np = self.render.attachNewNode(sun)
        self._sun_np.setPos(self._SUN_OFFSET)
        self._sun_np.lookAt(Point3(0, 0, 0))
        light_node = self._sun_np.node()
        get_initial_state = getattr(light_node, "getInitialState", None)
        set_initial_state = getattr(light_node, "setInitialState", None)
        if callable(get_initial_state) and callable(set_initial_state):
            shadow_state = get_initial_state()
            shadow_state = shadow_state.setAttrib(DepthOffsetAttrib.make(-3))
            set_initial_state(shadow_state)
        self.render.setLight(self._sun_np)

        self._setup_sky()
        self._add_sun_disc(self.SUN_POS)
        self.render.setShaderAuto()

    def _build_sky_texture(self):
        w, h = 1024, 512
        img = PNMImage(w, h, 3)

        horizon = (0.95, 0.80, 0.58)
        mid = (0.45, 0.66, 0.90)
        zenith = (0.12, 0.31, 0.62)

        for y in range(h):
            v = y / (h - 1)
            if v < 0.34:
                t = v / 0.34
                base_r = horizon[0] * (1.0 - t) + mid[0] * t
                base_g = horizon[1] * (1.0 - t) + mid[1] * t
                base_b = horizon[2] * (1.0 - t) + mid[2] * t
            else:
                t = (v - 0.34) / 0.66
                base_r = mid[0] * (1.0 - t) + zenith[0] * t
                base_g = mid[1] * (1.0 - t) + zenith[1] * t
                base_b = mid[2] * (1.0 - t) + zenith[2] * t

            haze = max(0.0, 1.0 - abs(v - 0.24) / 0.26)
            base_r = min(1.0, base_r + haze * 0.06)
            base_g = min(1.0, base_g + haze * 0.04)
            base_b = min(1.0, base_b + haze * 0.02)

            for x in range(w):
                u = x / (w - 1)
                n = (
                    math.sin(u * 22.0 + v * 9.0 + 0.8) * 0.52
                    + math.sin(u * 53.0 - v * 17.0 + 1.3) * 0.33
                    + math.cos(u * 81.0 + v * 29.0 - 0.7) * 0.15
                )
                n = n / 1.85
                cloud = max(0.0, min(1.0, (n * 0.5 + 0.5) - (0.48 + 0.34 * v)))
                cloud_alpha = cloud * (0.14 + 0.24 * max(0.0, 1.0 - v))

                r = base_r * (1.0 - cloud_alpha) + 0.96 * cloud_alpha
                g = base_g * (1.0 - cloud_alpha) + 0.97 * cloud_alpha
                b = base_b * (1.0 - cloud_alpha) + 0.98 * cloud_alpha
                img.setXel(x, y, r, g, b)

        tex = Texture("sky_gradient_clouds")
        tex.load(img)
        tex.setWrapU(Texture.WMRepeat)
        tex.setWrapV(Texture.WMClamp)
        tex.setMinfilter(Texture.FTLinearMipmapLinear)
        tex.setMagfilter(Texture.FTLinear)
        return tex

    def _setup_sky(self):
        main_mask = self.cam.node().getCameraMask()
        self._sky_np = self.loader.loadModel("models/misc/sphere")
        self._sky_np.reparentTo(self.render)
        self._sky_np.setScale(950.0)
        self._sky_np.setTwoSided(True)
        self._sky_np.setLightOff()
        self._sky_np.setShaderOff()
        self._sky_np.setDepthWrite(False)
        self._sky_np.setDepthTest(False)
        self._sky_np.setBin("background", 0)
        self._sky_np.hide(BitMask32.allOn())
        self._sky_np.show(main_mask)
        self._sky_np.setTexture(self._build_sky_texture(), 1)

    def _add_sun_disc(self, pos):
        main_mask = self.cam.node().getCameraMask()
        cm = CardMaker("sun_disc")
        cm.setFrame(-1, 1, -1, 1)

        layers = [
            (6.2, (1.0, 0.98, 0.84, 1.0)),
            (9.0, (1.0, 0.90, 0.60, 0.34)),
            (14.0, (1.0, 0.78, 0.42, 0.20)),
            (21.0, (1.0, 0.70, 0.36, 0.10)),
        ]
        self._sun_sprites = []
        for idx, (scale, color) in enumerate(layers):
            sp = self.render.attachNewNode(cm.generate())
            sp.setName(f"sun_layer_{idx}")
            sp.setPos(pos)
            sp.setBillboardPointEye()
            sp.setScale(scale)
            sp.setColor(*color)
            sp.setLightOff()
            sp.setShaderOff()
            sp.setDepthWrite(False)
            sp.setDepthTest(True)
            sp.setTransparency(True)
            sp.setBin("background", 1)
            sp.hide(BitMask32.allOn())
            sp.show(main_mask)
            self._sun_sprites.append(sp)

        # Subtle horizontal glare band.
        glare = self.render.attachNewNode(cm.generate())
        glare.setPos(pos)
        glare.setBillboardPointEye()
        glare.setScale(28.0, 1.0, 3.2)
        glare.setColor(1.0, 0.82, 0.47, 0.10)
        glare.setLightOff()
        glare.setShaderOff()
        glare.setDepthWrite(False)
        glare.setDepthTest(True)
        glare.setTransparency(True)
        glare.setBin("background", 1)
        glare.hide(BitMask32.allOn())
        glare.show(main_mask)
        self._sun_sprites.append(glare)

    def _setup_physics(self):
        self.bullet_world = BulletWorld()
        self.bullet_world.setGravity(Vec3(0, 0, -9.81))

    def _setup_scene(self):
        main_mask = self.cam.node().getCameraMask()

        self.terrain = Terrain(self.render, self.bullet_world)
        self.terrain.np.hide(BitMask32.allOn())
        self.terrain.np.show(main_mask)

        spawn_pose = SPAWN_POINTS[0]["pose"]["position"]
        self._spawn_point = tuple(spawn_pose)
        self.rover = Rover(self.render, self.bullet_world, start_pos=self._spawn_point)

        self._scene_object_nps = []
        self._solar_nps = []
        self._building_nps = []
        self._hub_nps = []
        self._stone_nps = []
        self._tree_nps = []
        self._obstacle_footprints = []

        self._create_scene_objects(main_mask)

        self._flip_timer   = 0.0

        self.cam_ctrl = CameraController(self, self.rover)
        self.gui      = TelemetryGUI()

    def _add_static_box_collider(self, name, x, y, z, hx, hy, hz):
        body = BulletRigidBodyNode(name)
        body.addShape(BulletBoxShape(Vec3(hx, hy, hz)))
        body.setMass(0.0)
        body.setFriction(1.25)
        body.setRestitution(0.0)
        body_np = self.render.attachNewNode(body)
        body_np.setPos(x, y, z)
        self.bullet_world.attachRigidBody(body)
        return body_np

    def _object_bucket(self, kind):
        if kind in ("solar_frame", "solar_panel", "pad"):
            return self._solar_nps
        if kind == "building":
            return self._building_nps
        if kind in ("charger", "guard_rail"):
            return self._hub_nps
        if kind in ("stone", "boulder"):
            return self._stone_nps
        if kind == "tree":
            return self._tree_nps
        return self._scene_object_nps

    def _create_box_object(self, spec, main_mask):
        meta = spec.get("metadata", {})
        geom = spec["geometry"]
        pose = spec["pose"]
        pos = pose["position"]
        hpr = pose["rotation_euler_deg"]
        hx, hy, hz = geom["half_extents"]

        if spec.get("collision") and (meta.get("visible") is False or spec["kind"] == "collision_proxy"):
            np = self._add_static_box_collider(spec["id"], pos[0], pos[1], pos[2], hx, hy, hz)
            self._object_bucket(spec["kind"]).append(np)
            return

        color = spec.get("material", {}).get("base_color", [0.6, 0.6, 0.6])
        np = self.render.attachNewNode(_build_box_node(spec["id"], hx, hy, hz, color))
        np.setPos(*pos)
        np.setHpr(*hpr)
        np.setTwoSided(True)
        np.hide(BitMask32.allOn())
        np.show(main_mask)
        self._object_bucket(spec["kind"]).append(np)

    def _create_ellipsoid_body_object(self, spec, main_mask):
        geom = spec["geometry"]
        pose = spec["pose"]
        pos = pose["position"]
        hpr = pose["rotation_euler_deg"]
        rx, ry, rz = geom["radii"]
        collision = spec.get("collision", {})
        radius = collision.get("radius", max(rx, ry, rz))

        node = BulletRigidBodyNode(spec["id"])
        node.addShape(BulletSphereShape(radius))
        node.setMass(0)
        body_np = self.render.attachNewNode(node)
        body_np.setPos(*pos)
        body_np.setHpr(*hpr)
        self.bullet_world.attachRigidBody(node)

        material = spec.get("material", {})
        rock_np = body_np.attachNewNode(_build_rock_node(
            f"{spec['id']}_visual",
            rx,
            ry,
            rz,
            seed=int(geom.get("seed", 0)),
            base_col=tuple(material.get("base_color", [0.44, 0.40, 0.35])),
            jitter=float(material.get("jitter", 0.07)),
        ))
        rock_np.setTwoSided(True)
        rock_np.hide(BitMask32.allOn())
        rock_np.show(main_mask)
        self._object_bucket(spec["kind"]).append(rock_np)

    def _create_compound_object(self, spec, main_mask):
        pose = spec["pose"]
        parent = self.render.attachNewNode(spec["id"])
        parent.setPos(*pose["position"])
        parent.setHpr(*pose["rotation_euler_deg"])

        for part in spec["geometry"].get("parts", []):
            if part["type"] != "ellipsoid":
                continue
            rx, ry, rz = part["radii"]
            material = part.get("material", {})
            part_np = parent.attachNewNode(_build_rock_node(
                f"{spec['id']}_{part['id']}",
                rx,
                ry,
                rz,
                seed=int(part.get("seed", 0)),
                base_col=tuple(material.get("base_color", [0.4, 0.4, 0.4])),
                jitter=float(material.get("jitter", 0.05)),
            ))
            part_np.setPos(*part.get("local_position", [0.0, 0.0, 0.0]))
            part_np.setTwoSided(True)

        parent.hide(BitMask32.allOn())
        parent.show(main_mask)
        self._object_bucket(spec["kind"]).append(parent)

    def _create_scene_objects(self, main_mask):
        for spec in SCENE_OBJECTS:
            geom_type = spec["geometry"]["type"]
            if geom_type == "box":
                self._create_box_object(spec, main_mask)
            elif geom_type == "ellipsoid":
                self._create_ellipsoid_body_object(spec, main_mask)
            elif geom_type == "compound":
                self._create_compound_object(spec, main_mask)

    def _reset_rover(self):
        """Teleport rover back to spawn with zeroed velocity (called after flip)."""
        cn = self.rover.chassis_np.node()
        self.rover.chassis_np.setPos(*self._spawn_point)
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
            telemetry_policy_getter=self._current_telemetry_policy,
            on_telemetry_policy_change=self._set_telemetry_policy,
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
        self._refresh_status_bar("disabled")

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
        self._refresh_status_bar(self._mqtt_bridge.status_text())

    def _current_telemetry_policy(self):
        mqtt_cfg = self._cfg.get("mqtt", {})
        return str(mqtt_cfg.get("telemetry_policy", "auto")).strip().lower()

    def _set_telemetry_policy(self, policy):
        policy = str(policy or "").strip().lower()
        if policy not in {"auto", "force_on", "force_off"}:
            return
        self._cfg.setdefault("mqtt", {})["telemetry_policy"] = policy
        save_settings(self._cfg)
        if self._settings_dlg:
            self._settings_dlg.populate(self._cfg)
        self._status.set_status(f"Telemetry policy set to {policy}")
        self._refresh_status_bar()

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

        gps = local_to_gps(pos, self._georeference)

        mqtt_cfg = self._cfg.get("mqtt", {})
        return {
            "timestamp": time.time(),
            "position": {"x": pos.x, "y": pos.y, "z": pos.z},
            "gps": gps,
            "georeference": self._georeference,
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
        if not self._mqtt_publish_enabled():
            return
        hz = max(1, int(self._cfg["mqtt"]["telemetry_hz"]))
        period = 1.0 / hz
        if now_mono - self._last_state_pub_mono < period:
            return
        self._last_state_pub_mono = now_mono
        self._mqtt_bridge.publish_state(payload)

    def _mqtt_publish_enabled(self):
        mqtt_cfg = self._cfg.get("mqtt", {})
        policy = str(mqtt_cfg.get("telemetry_policy", "auto")).strip().lower()
        if policy == "force_on":
            return True
        if policy == "force_off":
            return False
        timeout_s = max(0.0, float(mqtt_cfg.get("gcs_presence_timeout_ms", 120000)) / 1000.0)
        return self._mqtt_bridge.has_active_gcs(timeout_s)

    def _refresh_status_bar(self, mqtt_state=None):
        mqtt_cfg = self._cfg.get("mqtt", {})
        self._status.set_mqtt_state(
            mqtt_state if mqtt_state is not None else self._mqtt_bridge.status_text(),
            mode=mqtt_cfg["control_mode"],
            control_hz=mqtt_cfg["control_hz"],
            telemetry_hz=mqtt_cfg["telemetry_hz"],
            telemetry_policy=mqtt_cfg.get("telemetry_policy", "auto"),
            telemetry_enabled=self._mqtt_publish_enabled() if hasattr(self, "_mqtt_bridge") else False,
        )

    def _publish_video_if_due(self, now_mono):
        if not self._mqtt_publish_enabled():
            return
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
        dt = min(globalClock.getDt(), 1.0 / 30.0)
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
        self.bullet_world.doPhysics(dt, 8, 1.0 / 120.0)

        # Flip detection: rover up-vector Z < 0 means upside-down (past 90°)
        up = self.rover.chassis_np.getQuat(self.render).xform(Vec3(0, 0, 1))
        if up.z < 0.0:
            self._flip_timer += dt
            if self._flip_timer >= 2.0:
                self._reset_rover()
                self._flip_timer = 0.0
        else:
            self._flip_timer = 0.0

        cam_pos = self.camera.getPos(self.render)
        self._sky_np.setPos(cam_pos)
        for sp in self._sun_sprites:
            sp.setPos(cam_pos + self.SUN_POS)
        self.cam_ctrl.update()
        state_payload = self._collect_state_payload()
        self._publish_state_if_due(now_mono, state_payload)
        self._publish_video_if_due(now_mono)
        self.gui.update_from_state(state_payload)
        self._refresh_status_bar()
        self._status.set_telemetry(self.rover.pos, self.rover.heading, self.rover.speed)
        return task.cont


if __name__ == "__main__":
    app = RoverSimulator()
    app.run()
