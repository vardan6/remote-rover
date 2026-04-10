import math
from panda3d.core import Vec3, LColor, Point3, TransformState
from panda3d.bullet import BulletRigidBodyNode, BulletBoxShape, BulletVehicle, ZUp
from panda3d.core import (GeomNode, Geom, GeomTriangles, GeomVertexData,
                          GeomVertexFormat, GeomVertexWriter)


# ── Rover body dimensions (metres) ───────────────────────────────────────────
# These define the physical size of the chassis box (half-extents).
# Changing them scales the collision shape AND the visual mesh together.
HALF_W = 0.4    # half-width  — wider = more lateral stability, harder to tip sideways
HALF_L = 0.6    # half-length — longer wheelbase = more stable straight-line driving
HALF_H = 0.11   # half-height of body box — lower CoM when small; affects visual silhouette

# ── Wheel geometry ────────────────────────────────────────────────────────────
WHEEL_RADIUS   = 0.25   # metres — larger radius clears bigger obstacles; affects ride height
WHEEL_WIDTH    = 0.2    # metres — wider tyre gives more grip contact patch (visual only here)
WHEEL_SEGMENTS = 32     # polygon count for wheel cylinder mesh — purely visual detail level

# ── Drive / control ───────────────────────────────────────────────────────────
CHASSIS_MASS      = 210.0  # kg — heavier = more inertia (resists flipping/flopping) but
                             #      needs more engine force; also lowers effective suspension
                             #      frequency (softer feel for same spring stiffness)
MAX_ENGINE_FORCE  = 620.0  # N per wheel (all 4 driven) — total thrust = 4 × this value.
                             #      Scale proportionally when changing CHASSIS_MASS so
                             #      acceleration stays roughly constant (a = F/m)
MAX_BRAKE_FORCE   = 360.0   # N per wheel when coasting with no throttle input.
                             #      Higher = shorter stopping distance, snappier feel
MAX_STEER_ANGLE   = 28.0    # degrees — maximum front-wheel steering angle.
                             #      More = tighter turning circle but more oversteer tendency
ENGINE_FORCE_RESPONSE = 6.0  # 1/s — higher = throttle engages faster.
                               # Smooth force application avoids instant torque spikes
                               # that can pop the front wheels up.
GROUND_STICK_FORCE_BASE = 220.0   # N — extra downward force to keep tyres planted.
GROUND_STICK_FORCE_PER_KMH = 8.0  # N/(km/h) — more speed => more downforce.

# ── Suspension ────────────────────────────────────────────────────────────────
# Bullet equilibrium formula:  compression_at_rest [m] = g / SUSPENSION_STIFFNESS
# → STIFFNESS=10 ≈ 0.98 m rest compression (likely bottomed out for 25 cm travel)
# → STIFFNESS=40 ≈ 0.25 m rest compression (sits right at travel limit)
# → STIFFNESS=60 ≈ 0.16 m rest compression (comfortable mid-travel)
# Rule of thumb: STIFFNESS > (g / (MAX_TRAVEL_CM/100)) to avoid bottoming out.
#   For 25 cm travel:  STIFFNESS > 9.81/0.25 = 39.2  →  use 50–80 for headroom.
SUSPENSION_STIFFNESS        = 52.0   # spring rate — higher = stiffer, chassis tilts less
                                      # on slopes/bumps; lower = softer ride but more flop
                                      # CRITICAL: must satisfy g/stiffness < MAX_TRAVEL/100
                                      # or suspension bottoms out (9.81/70 = 0.14 m < 0.20 m ✓)
SUSPENSION_DAMPING_RELAX    = 4.0    # damping on spring extension (rebound).
                                      # Higher = oscillations die faster after a bump.
                                      # Too high = feels like the wheels slam down hard
SUSPENSION_DAMPING_COMPRESS = 5.8    # damping on spring compression (bump).
                                      # Higher = softer impact over obstacles.
                                      # Too high = chassis barely moves (rigid feel)
SUSPENSION_REST_LENGTH      = 0.20   # m — nominal spring length at standstill.
                                      # Explicitly setting this avoids Bullet's long
                                      # default rest-length, which can leave the chassis
                                      # riding too high and wheelie-prone.
SUSPENSION_MAX_TRAVEL_CM    = 28.0   # cm — total suspension stroke.
                                      # Shorter = less chassis pitch/roll range (stabler);
                                      # longer = wheels track rougher terrain but chassis
                                      # tips more dramatically on steep slopes
MAX_SUSPENSION_FORCE        = 4300.0  # N per wheel — caps suspension load.
                                       # Keeps the chassis from over-extending/rebounding
                                       # aggressively during hard throttle transitions.

# ── Wheel–ground contact ─────────────────────────────────────────────────────
WHEEL_FRICTION    = 3.8   # friction coefficient for wheel–terrain contact.
                           # Higher = more grip (less sliding on slopes/corners);
                           # lower = wheels slip, rover drifts (realistic on loose soil)
ROLL_INFLUENCE    = 0.20  # [0..1] fraction of chassis roll transferred to suspension.
                           # 0 = full anti-roll (arcade, very stable, wheels lift off terrain);
                           # 1 = no anti-roll correction (realistic, tips easily on slopes).
                           # 0.1–0.3 is a good balance for a compact rover

# ── Chassis rigid-body damping ────────────────────────────────────────────────
# Applied directly to the Bullet rigid body, independent of suspension.
CHASSIS_LINEAR_DAMPING  = 0.20   # [0..1] simulates air drag / rolling resistance.
                                   # Higher = slows down faster when throttle released;
                                   # 0 = coasts indefinitely (no drag at all)
CHASSIS_ANGULAR_DAMPING = 0.45   # [0..1] resists rotation of the chassis body.
                                   # Higher = less tumbling/spinning after a tip;
                                   # too high (→1) feels magnetically glued upright
CHASSIS_ANGULAR_FACTOR  = 0.70   # [0..1] scales torques that pitch (front/back tilt) and
                                   # roll (side tilt) the chassis — applied as Vec3(factor, factor, 1.0)
                                   # so yaw (steering) remains unrestricted.
                                   # 0 = chassis cannot pitch or roll at all (fully arcade);
                                   # 1 = full rotation (realistic but wheelie/flip-prone).
                                   # 0.15–0.35 prevents throttle-wheelies and side flips while
                                   # still allowing the body to conform to moderate terrain slopes.

# ── Anti-wheelie controls ─────────────────────────────────────────────────────
# These activate only during forward throttle when front wheels unload.
ANTI_WHEELIE_PITCH_START_DEG   = 12.0   # start limiting when nose-up exceeds this.
ANTI_WHEELIE_PITCH_CUTOFF_DEG  = 24.0   # fully cut engine by this pitch if front unloaded.
ANTI_WHEELIE_SINGLE_CONTACT    = 0.86   # engine scale if only 1 front wheel touches.
ANTI_WHEELIE_NO_FRONT_CONTACT  = 0.60   # engine scale if both front wheels are airborne.

# ── Visual body Z offset ──────────────────────────────────────────────────────
# Shifts the rendered body mesh relative to the chassis centre-of-mass node.
# Physics is unaffected — this is purely a cosmetic adjustment.
# Positive = body appears higher on the chassis; negative = lower / buried in wheels.
BODY_VISUAL_Z_OFFSET = -HALF_H * 2  # shifts body DOWN; negative = lower on the chassis.

# ── Chassis collision shape offset ───────────────────────────────────────────
# The BulletBoxShape is added with a +Z offset so the physics box sits ABOVE
# the chassis node's origin.  Wheel connection points sit at the origin (z=0),
# below the box bottom, so the wheel raycasts don't self-intersect the chassis.
_CHASSIS_SHAPE_OFFSET = HALF_H   # box occupies [0, 2*HALF_H] in chassis-local Z

# ── Wheel attachment geometry ─────────────────────────────────────────────────
# These control where the four suspension connection points attach to the chassis.
# Vehicle moves in the +Y direction (ZUp coordinate system).
# Indices 0,1  = +Y side = "front" (steering)
# Indices 2,3  = -Y side = "rear"  (driven)
WHEEL_LATERAL_CLEARANCE    = 0.02   # m — gap between chassis side and wheel inner edge.
                                     # Increase for wider track (more lateral stability);
                                     # decrease to bring wheels closer to body
WHEEL_LONGITUDINAL_INSET   = 0.18   # m — wheels are set this far inward from the
                                     # chassis front/rear ends.  Smaller inset = longer
                                     # effective wheelbase = more straight-line stability;
                                     # larger inset = shorter wheelbase = tighter turns

_CONN_X = HALF_W + WHEEL_WIDTH / 2 + WHEEL_LATERAL_CLEARANCE
_CONN_Y = HALF_L - WHEEL_LONGITUDINAL_INSET

WHEEL_SETUPS = [
    # (connection_point_local,           is_front)
    (Point3(-_CONN_X,  _CONN_Y, 0.0),   True),   # 0: front-left
    (Point3( _CONN_X,  _CONN_Y, 0.0),   True),   # 1: front-right
    (Point3(-_CONN_X, -_CONN_Y, 0.0),   False),  # 2: rear-left
    (Point3( _CONN_X, -_CONN_Y, 0.0),   False),  # 3: rear-right
]


# ── Geometry helpers ──────────────────────────────────────────────────────────
def _build_body_node():
    hw, hl, hh = HALF_W, HALF_L, HALF_H
    verts = [
        (-hw, -hl, -hh), (hw, -hl, -hh), (hw, hl, -hh), (-hw, hl, -hh),
        (-hw, -hl,  hh), (hw, -hl,  hh), (hw, hl,  hh), (-hw, hl,  hh),
    ]
    # Warm orange-red palette with subtle face variation so lighting still reads shape.
    faces = [
        ((0, 1, 2, 3), LColor(0.78, 0.24, 0.08, 1), ( 0,  0, -1)),  # bottom
        ((4, 7, 6, 5), LColor(0.88, 0.30, 0.08, 1), ( 0,  0,  1)),  # top
        ((0, 4, 5, 1), LColor(0.96, 0.36, 0.09, 1), ( 0, -1,  0)),  # front (brightest)
        ((1, 5, 6, 2), LColor(0.82, 0.25, 0.08, 1), ( 1,  0,  0)),  # right
        ((2, 6, 7, 3), LColor(0.76, 0.22, 0.07, 1), ( 0,  1,  0)),  # back
        ((3, 7, 4, 0), LColor(0.82, 0.25, 0.08, 1), (-1,  0,  0)),  # left
    ]
    fmt   = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData("rover_body", fmt, Geom.UHStatic)
    vdata.setNumRows(24)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")
    tris = GeomTriangles(Geom.UHStatic)
    base = 0
    for face_verts, col, norm in faces:
        for vi in face_verts:
            vw.addData3(*verts[vi])
            nw.addData3(*norm)
            cw.addData4(col)
        tris.addVertices(base, base + 1, base + 2)
        tris.addVertices(base, base + 2, base + 3)
        base += 4
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode("rover_body")
    gn.addGeom(geom)
    return gn


def _build_wheel_node(name):
    hw, r = WHEEL_WIDTH / 2.0, WHEEL_RADIUS
    fmt   = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHDynamic)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")
    tris = GeomTriangles(Geom.UHStatic)
    idx = 0
    for i in range(WHEEL_SEGMENTS):
        a0 = 2 * math.pi * i / WHEEL_SEGMENTS
        a1 = 2 * math.pi * (i + 1) / WHEEL_SEGMENTS
        col = LColor(0.18, 0.18, 0.18, 1) if (i // 2) % 2 == 0 else LColor(0.28, 0.28, 0.28, 1)
        for (x, a) in [(-hw, a0), (-hw, a1), (hw, a1), (hw, a0)]:
            vw.addData3(x, math.cos(a) * r, math.sin(a) * r)
            nw.addData3(0, math.cos(a), math.sin(a))
            cw.addData4(col)
        tris.addVertices(idx, idx + 1, idx + 2)
        tris.addVertices(idx, idx + 2, idx + 3)
        idx += 4
    hub = LColor(0.55, 0.55, 0.60, 1)
    for side, nx in [(-hw, -1.0), (hw, 1.0)]:
        ci = idx
        vw.addData3(side, 0, 0); nw.addData3(nx, 0, 0); cw.addData4(hub); idx += 1
        for i in range(WHEEL_SEGMENTS):
            a = 2 * math.pi * i / WHEEL_SEGMENTS
            vw.addData3(side, math.cos(a) * r, math.sin(a) * r)
            nw.addData3(nx, 0, 0); cw.addData4(hub)
        for i in range(WHEEL_SEGMENTS):
            i0, i1 = ci + 1 + i, ci + 1 + (i + 1) % WHEEL_SEGMENTS
            if nx > 0: tris.addVertices(ci, i0, i1)
            else:      tris.addVertices(ci, i1, i0)
        idx += WHEEL_SEGMENTS
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode(name)
    gn.addGeom(geom)
    return gn


# ── Rover ─────────────────────────────────────────────────────────────────────
class Rover:
    def __init__(self, render, bullet_world, start_pos=(0, 0, 3)):
        self._render = render
        self._world  = bullet_world
        self.throttle = 0.0
        self.steering = 0.0
        self._engine_force = 0.0

        # ── Chassis rigid body ────────────────────────────────────────────────
        # Shape is offset +Z so its bottom sits at the chassis origin;
        # wheel connection points (at z=0) are below the box, keeping
        # the wheel raycasts from self-colliding with the chassis shape.
        shape = BulletBoxShape(Vec3(HALF_W, HALF_L, HALF_H))
        chassis_node = BulletRigidBodyNode("rover")
        chassis_node.addShape(
            shape,
            TransformState.makePos(Point3(0, 0, _CHASSIS_SHAPE_OFFSET))
        )
        chassis_node.setMass(CHASSIS_MASS)
        chassis_node.setDeactivationEnabled(False)
        chassis_node.setLinearDamping(CHASSIS_LINEAR_DAMPING)
        chassis_node.setAngularDamping(CHASSIS_ANGULAR_DAMPING)
        chassis_node.setAngularFactor(Vec3(CHASSIS_ANGULAR_FACTOR, CHASSIS_ANGULAR_FACTOR, 1.0))
        chassis_node.setFriction(1.15)
        if hasattr(chassis_node, "setCcdMotionThreshold"):
            chassis_node.setCcdMotionThreshold(0.03)
            chassis_node.setCcdSweptSphereRadius(0.24)

        self.chassis_np = render.attachNewNode(chassis_node)
        self.chassis_np.setPos(*start_pos)
        bullet_world.attachRigidBody(chassis_node)

        # ── Visual rover body ─────────────────────────────────────────────────
        body_np = self.chassis_np.attachNewNode(_build_body_node())
        body_np.setZ(BODY_VISUAL_Z_OFFSET)
        body_np.setTwoSided(True)
        body_np.setTransparency(False)

        # ── BulletVehicle (raycast suspension) ────────────────────────────────
        self.vehicle = BulletVehicle(bullet_world, chassis_node)
        self.vehicle.setCoordinateSystem(ZUp)
        bullet_world.attachVehicle(self.vehicle)

        # ── Wheels ────────────────────────────────────────────────────────────
        self._wheel_nps = []
        for i, (conn_pt, is_front) in enumerate(WHEEL_SETUPS):
            # Visual wheel node (world-parented so physics can set its transform)
            wn = render.attachNewNode(_build_wheel_node(f"wheel_{i}"))
            self._wheel_nps.append(wn)

            wheel = self.vehicle.createWheel()
            wheel.setChassisConnectionPointCs(conn_pt)
            wheel.setFrontWheel(is_front)
            wheel.setWheelDirectionCs(Vec3(0, 0, -1))   # suspension direction: down
            wheel.setWheelAxleCs(Vec3(1, 0, 0))         # spin axis: X
            wheel.setWheelRadius(WHEEL_RADIUS)
            if hasattr(wheel, "setSuspensionRestLength"):
                wheel.setSuspensionRestLength(SUSPENSION_REST_LENGTH)
            elif hasattr(wheel, "set_suspension_rest_length"):
                wheel.set_suspension_rest_length(SUSPENSION_REST_LENGTH)
            elif hasattr(type(wheel), "suspension_rest_length"):
                # Some Panda3D builds expose this as a property.
                try:
                    wheel.suspension_rest_length = SUSPENSION_REST_LENGTH
                except (AttributeError, TypeError):
                    pass
            wheel.setMaxSuspensionTravelCm(SUSPENSION_MAX_TRAVEL_CM)
            if hasattr(wheel, "setMaxSuspensionForce"):
                wheel.setMaxSuspensionForce(MAX_SUSPENSION_FORCE)
            else:
                wheel.set_max_suspension_force(MAX_SUSPENSION_FORCE)
            wheel.setSuspensionStiffness(SUSPENSION_STIFFNESS)
            wheel.setWheelsDampingRelaxation(SUSPENSION_DAMPING_RELAX)
            wheel.setWheelsDampingCompression(SUSPENSION_DAMPING_COMPRESS)
            wheel.setFrictionSlip(WHEEL_FRICTION)
            wheel.setRollInfluence(ROLL_INFLUENCE)
            # Auto-sync the visual node's transform with wheel physics each step
            wheel.setNode(wn.node())

    # ── per-frame update ──────────────────────────────────────────────────────
    def update(self, dt):
        contact_count = self._count_wheel_contacts()

        target_engine = self.throttle * MAX_ENGINE_FORCE
        blend = min(1.0, ENGINE_FORCE_RESPONSE * dt)
        self._engine_force += (target_engine - self._engine_force) * blend

        engine = self._engine_force
        if contact_count == 0:
            engine = 0.0
        elif contact_count == 1:
            engine *= 0.40

        if self.throttle > 0.0:
            engine *= self._anti_wheelie_scale()

        brake = MAX_BRAKE_FORCE if abs(self.throttle) < 1e-4 else 0.0

        for i in range(4):
            self.vehicle.applyEngineForce(engine, i)
            self.vehicle.setBrake(brake, i)

        # Keep chassis planted so wheel contact is maintained on uneven terrain.
        if abs(self.throttle) > 1e-4 or contact_count < 4:
            speed_kmh = abs(self.vehicle.getCurrentSpeedKmHour())
            downforce = GROUND_STICK_FORCE_BASE + speed_kmh * GROUND_STICK_FORCE_PER_KMH
            if contact_count <= 2:
                downforce *= 1.35
            self._apply_central_force(Vec3(0, 0, -downforce))

        # Steering on front wheels (indices 0 and 1)
        steer = self.steering * MAX_STEER_ANGLE
        self.vehicle.setSteeringValue( steer, 0)
        self.vehicle.setSteeringValue( steer, 1)

    def _anti_wheelie_scale(self):
        """Limit throttle only when the front axle starts unloading."""
        contacts = 0
        for i in (0, 1):
            if self._wheel_is_in_contact(i):
                contacts += 1

        if contacts == 2:
            return 1.0

        front = self.chassis_np.getQuat(self._render).xform(Vec3(0, 1, 0))
        pitch_deg = math.degrees(math.asin(max(-1.0, min(1.0, front.z))))

        if contacts == 1:
            contact_scale = ANTI_WHEELIE_SINGLE_CONTACT
        else:
            contact_scale = ANTI_WHEELIE_NO_FRONT_CONTACT

        if pitch_deg <= ANTI_WHEELIE_PITCH_START_DEG:
            return contact_scale
        if pitch_deg >= ANTI_WHEELIE_PITCH_CUTOFF_DEG:
            return 0.0

        t = (
            (pitch_deg - ANTI_WHEELIE_PITCH_START_DEG)
            / (ANTI_WHEELIE_PITCH_CUTOFF_DEG - ANTI_WHEELIE_PITCH_START_DEG)
        )
        pitch_scale = 1.0 - t
        return min(contact_scale, pitch_scale)

    def _wheel_is_in_contact(self, wheel_idx):
        if hasattr(self.vehicle, "getWheel"):
            wheel = self.vehicle.getWheel(wheel_idx)
        else:
            wheel = self.vehicle.get_wheel(wheel_idx)
        if hasattr(wheel, "getRaycastInfo"):
            ray = wheel.getRaycastInfo()
        else:
            ray = wheel.get_raycast_info()

        if hasattr(ray, "isInContact"):
            return bool(ray.isInContact())
        return bool(ray.is_in_contact())

    def _count_wheel_contacts(self):
        return sum(1 for i in range(4) if self._wheel_is_in_contact(i))

    def _apply_central_force(self, force):
        node = self.chassis_np.node()
        if hasattr(node, "applyCentralForce"):
            node.applyCentralForce(force)
        else:
            node.apply_central_force(force)

    def reset_drive_state(self):
        self.throttle = 0.0
        self.steering = 0.0
        self._engine_force = 0.0

    # ── properties ────────────────────────────────────────────────────────────
    @property
    def pos(self):
        return self.chassis_np.getPos()

    @property
    def heading(self):
        return self.chassis_np.getH()

    @property
    def speed(self):
        return abs(self.vehicle.getCurrentSpeedKmHour())   # km/h

    @property
    def wheel_nps(self):
        return self._wheel_nps
