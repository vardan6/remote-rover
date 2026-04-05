import math
from panda3d.core import (
    NodePath, Camera, PerspectiveLens, Vec3, Point3,
    FrameBufferProperties, WindowProperties, GraphicsPipe,
    GraphicsOutput
)


# Follow-cam defaults
FOLLOW_DIST_DEFAULT = 8.0
FOLLOW_DIST_MIN     = 2.0
FOLLOW_DIST_MAX     = 30.0
ELEVATION_DEFAULT   = 20.0   # degrees above horizontal
ELEVATION_MIN       = 3.0
ELEVATION_MAX       = 85.0

# Sensitivity
ORBIT_SENSITIVITY   = 0.3    # degrees per pixel
ZOOM_STEP           = 1.2    # multiply/divide distance per scroll click

POV_FORWARD_OFFSET = 0.65
POV_HEIGHT_OFFSET  = 0.25
POV_FOV  = 90.0
POV_W, POV_H = 640, 480


class CameraController:
    def __init__(self, base, rover):
        self._base = base
        self._rover = rover
        self._pov_active  = False
        self._pov_buffer  = None
        self._pov_cam_np  = None

        # Orbital state (follow cam)
        self._azimuth   = 0.0               # degrees; 0 = directly behind rover
        self._elevation = ELEVATION_DEFAULT  # degrees above horizontal
        self._dist      = FOLLOW_DIST_DEFAULT

        # Mouse drag state
        self._dragging     = False
        self._last_mouse_x = 0.0
        self._last_mouse_y = 0.0

        base.disableMouse()
        self._setup_follow_cam()
        self._setup_pov_cam()
        self._setup_mouse_events()

    # ------------------------------------------------------------------
    def _setup_follow_cam(self):
        base = self._base
        base.camera.reparentTo(base.render)
        base.camLens.setFov(60)
        base.camLens.setNear(0.1)
        base.camLens.setFar(500)

    def _setup_pov_cam(self):
        base = self._base
        fb_props = FrameBufferProperties()
        fb_props.setRgbColor(True)
        fb_props.setDepthBits(24)

        win_props = WindowProperties.size(POV_W, POV_H)

        self._pov_buffer = base.graphicsEngine.makeOutput(
            base.pipe, "pov_buffer", -2,
            fb_props, win_props,
            GraphicsPipe.BFRefuseWindow | GraphicsPipe.BFResizeable,
            base.win.getGsg(), base.win,
        )

        if self._pov_buffer is None:
            print("[camera] Warning: could not create POV offscreen buffer")
            return

        pov_cam_node = Camera("pov_cam")
        lens = PerspectiveLens()
        lens.setFov(POV_FOV)
        lens.setNear(0.1)
        lens.setFar(300)
        pov_cam_node.setLens(lens)

        self._pov_cam_np = base.render.attachNewNode(pov_cam_node)
        dr = self._pov_buffer.makeDisplayRegion()
        dr.setCamera(self._pov_cam_np)
        self._pov_buffer.setActive(False)

    def _setup_mouse_events(self):
        base = self._base
        # Right-click drag to orbit
        base.accept("mouse3",    self._start_drag)
        base.accept("mouse3-up", self._stop_drag)
        # Scroll wheel to zoom
        base.accept("wheel_up",   self._zoom_in)
        base.accept("wheel_down", self._zoom_out)

    # ------------------------------------------------------------------
    def _start_drag(self):
        self._dragging = True
        mw = self._base.mouseWatcherNode
        if mw.hasMouse():
            self._last_mouse_x = mw.getMouseX()
            self._last_mouse_y = mw.getMouseY()

    def _stop_drag(self):
        self._dragging = False

    def _zoom_in(self):
        self._dist = max(FOLLOW_DIST_MIN, self._dist / ZOOM_STEP)

    def _zoom_out(self):
        self._dist = min(FOLLOW_DIST_MAX, self._dist * ZOOM_STEP)

    def _update_drag(self):
        if not self._dragging:
            return
        mw = self._base.mouseWatcherNode
        if not mw.hasMouse():
            return
        mx = mw.getMouseX()
        my = mw.getMouseY()
        dx = mx - self._last_mouse_x
        dy = my - self._last_mouse_y
        self._last_mouse_x = mx
        self._last_mouse_y = my

        # Scale from normalised [-1,1] to pixels
        win = self._base.win
        dx *= win.getXSize() * 0.5
        dy *= win.getYSize() * 0.5

        self._azimuth   -= dx * ORBIT_SENSITIVITY
        self._elevation  = max(ELEVATION_MIN,
                               min(ELEVATION_MAX,
                                   self._elevation + dy * ORBIT_SENSITIVITY))

    # ------------------------------------------------------------------
    def toggle(self):
        self._pov_active = not self._pov_active
        if self._pov_buffer:
            self._pov_buffer.setActive(self._pov_active)

    @property
    def pov_active(self):
        return self._pov_active

    # ------------------------------------------------------------------
    def update(self):
        self._update_drag()

        rover    = self._rover
        pos      = rover.pos
        rover_np = rover.chassis_np

        if self._pov_active:
            forward = rover_np.getQuat(self._base.render).xform(Vec3(0, 1, 0))
            up      = Vec3(0, 0, 1)
            cam_pos = pos + forward * POV_FORWARD_OFFSET + up * POV_HEIGHT_OFFSET
            if self._pov_cam_np:
                self._pov_cam_np.setPos(cam_pos)
                self._pov_cam_np.setHpr(rover_np.getHpr(self._base.render))
            self._base.camera.setPos(cam_pos)
            self._base.camera.setHpr(rover_np.getHpr(self._base.render))
        else:
            # Orbital follow cam: spherical coords around rover
            # azimuth=0 → behind rover (+rover heading), elevation=0 → horizontal
            rover_heading = rover_np.getH(self._base.render)
            az_rad = math.radians(rover_heading + self._azimuth)
            el_rad = math.radians(self._elevation)

            offset = Vec3(
                 math.sin(az_rad) * math.cos(el_rad),
                -math.cos(az_rad) * math.cos(el_rad),
                 math.sin(el_rad),
            ) * self._dist

            cam_pos = pos + offset
            self._base.camera.setPos(cam_pos)
            self._base.camera.lookAt(Point3(pos.x, pos.y, pos.z + 0.5))

    @property
    def pov_buffer(self):
        return self._pov_buffer
