from panda3d.core import (
    GeomNode, Geom, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexWriter, PNMImage
)
from panda3d.bullet import BulletRigidBodyNode, BulletHeightfieldShape, ZUp
import math


TERRAIN_SIZE = 400
TILE_COUNT = 320

SCENE_LAYOUT = {
    "plant_a": {
        "center": (-108.0, -84.0),
        "pad_half_extents": (26.0, 17.0),
        "floor_z": -5.2,
        "loop_half_extents": (37.0, 26.0),
    },
    "plant_b": {
        "center": (112.0, 82.0),
        "pad_half_extents": (26.0, 17.0),
        "floor_z": -4.6,
        "loop_half_extents": (37.0, 26.0),
    },
    "building": {
        "center": (0.0, -2.0),
        "pad_half_extents": (18.0, 13.0),
        "floor_z": -1.6,
    },
    "start_hub": {
        "center": (0.0, 20.0),
        "pad_half_extents": (13.0, 9.0),
        "surround_half_extents": (40.0, 30.0),
        "floor_z": -0.8,
    },
    "roads": {
        "width": 7.5,
        "feather": 12.0,
    },
    "spawn": {
        "xy": (0.0, 20.0),
    },
}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0.0
    t = _clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _dist_point_to_segment(px, py, ax, ay, bx, by):
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    denom = abx * abx + aby * aby
    if denom <= 1e-9:
        return math.hypot(px - ax, py - ay), 0.0
    t = _clamp((apx * abx + apy * aby) / denom, 0.0, 1.0)
    cx = ax + t * abx
    cy = ay + t * aby
    return math.hypot(px - cx, py - cy), t


def _rect_loop_points(cx, cy, hx, hy):
    return [
        (cx - hx, cy - hy),
        (cx + hx, cy - hy),
        (cx + hx, cy + hy),
        (cx - hx, cy + hy),
        (cx - hx, cy - hy),
    ]


def _polyline_segments(points):
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def _road_segments():
    pa = SCENE_LAYOUT["plant_a"]
    pb = SCENE_LAYOUT["plant_b"]
    bld = SCENE_LAYOUT["building"]
    hub = SCENE_LAYOUT["start_hub"]

    loop_a = _rect_loop_points(*pa["center"], *pa["loop_half_extents"])
    loop_b = _rect_loop_points(*pb["center"], *pb["loop_half_extents"])

    connect_plants = [
        (pa["center"][0], pa["center"][1] + pa["loop_half_extents"][1]),
        (0.0, 36.0),
        (pb["center"][0], pb["center"][1] - pb["loop_half_extents"][1]),
    ]
    connect_building_a = [
        bld["center"],
        (-46.0, -38.0),
        (pa["center"][0] + pa["loop_half_extents"][0], pa["center"][1]),
    ]
    connect_building_b = [
        bld["center"],
        (44.0, 34.0),
        (pb["center"][0] - pb["loop_half_extents"][0], pb["center"][1]),
    ]
    connect_start_hub = [
        hub["center"],
        (0.0, 8.0),
        bld["center"],
    ]

    segments = []

    for p0, p1 in _polyline_segments(loop_a):
        segments.append((p0, p1, pa["floor_z"], pa["floor_z"]))
    for p0, p1 in _polyline_segments(loop_b):
        segments.append((p0, p1, pb["floor_z"], pb["floor_z"]))

    plant_connector_nodes = [
        (connect_plants[0], pa["floor_z"]),
        (connect_plants[1], -2.3),
        (connect_plants[2], pb["floor_z"]),
    ]
    for i in range(len(plant_connector_nodes) - 1):
        (p0, z0) = plant_connector_nodes[i]
        (p1, z1) = plant_connector_nodes[i + 1]
        segments.append((p0, p1, z0, z1))

    a_nodes = [
        (connect_building_a[0], bld["floor_z"]),
        (connect_building_a[1], -2.5),
        (connect_building_a[2], pa["floor_z"]),
    ]
    b_nodes = [
        (connect_building_b[0], bld["floor_z"]),
        (connect_building_b[1], -2.2),
        (connect_building_b[2], pb["floor_z"]),
    ]
    for nodes in (a_nodes, b_nodes):
        for i in range(len(nodes) - 1):
            (p0, z0) = nodes[i]
            (p1, z1) = nodes[i + 1]
            segments.append((p0, p1, z0, z1))

    hub_nodes = [
        (connect_start_hub[0], hub["floor_z"]),
        (connect_start_hub[1], -1.2),
        (connect_start_hub[2], bld["floor_z"]),
    ]
    for i in range(len(hub_nodes) - 1):
        (p0, z0) = hub_nodes[i]
        (p1, z1) = hub_nodes[i + 1]
        segments.append((p0, p1, z0, z1))

    return segments


ROAD_SEGMENTS = _road_segments()


# Valley/hill shaping controls.
_VALLEYS = [
    (-108.0, -84.0, 58.0, 10.0),
    (112.0, 82.0, 60.0, 9.6),
]

_HILLS = [
    (-150.0, -18.0, 50.0, 8.0),
    (-48.0, -146.0, 44.0, 7.2),
    (148.0, 22.0, 52.0, 8.4),
    (42.0, 142.0, 45.0, 7.0),
    (0.0, -178.0, 38.0, 6.2),
    (0.0, 176.0, 36.0, 5.8),
]


def _gaussian_2d(x, y, cx, cy, sigma):
    dx = x - cx
    dy = y - cy
    d2 = dx * dx + dy * dy
    return math.exp(-d2 / (2.0 * sigma * sigma))


def _mix3(a, b, t):
    return (
        a[0] * (1.0 - t) + b[0] * t,
        a[1] * (1.0 - t) + b[1] * t,
        a[2] * (1.0 - t) + b[2] * t,
    )


def _terrain_noise(x, y):
    # Lightweight pseudo-noise (deterministic, no checker tiling).
    xn = x / TERRAIN_SIZE
    yn = y / TERRAIN_SIZE
    n = 0.0
    n += math.sin(xn * 31.0 + yn * 15.0 + 0.6) * 0.52
    n += math.cos(xn * -23.0 + yn * 27.0 - 1.9) * 0.33
    n += math.sin(xn * 62.0 - yn * 58.0 + 2.3) * 0.15
    return _clamp(n * 0.5 + 0.5, 0.0, 1.0)


def _terrain_color(x, y, h, slope_mag, road_mix):
    valley_mix = _smoothstep(-2.0, -8.5, h)
    high_mix = _smoothstep(4.0, 11.0, h)
    steep_mix = _smoothstep(0.26, 0.72, slope_mag)
    dry_noise = _terrain_noise(x, y)

    grass_rich = (0.20, 0.43, 0.16)
    grass_wet = (0.15, 0.35, 0.14)
    soil = (0.42, 0.34, 0.22)
    rock = (0.45, 0.43, 0.40)
    road = (0.35, 0.33, 0.29)

    base_grass = _mix3(grass_wet, grass_rich, 0.35 + 0.65 * dry_noise)
    valley_grass = _mix3(base_grass, (0.12, 0.32, 0.14), valley_mix * 0.7)
    soil_mix = _smoothstep(0.22, 0.74, dry_noise + slope_mag * 0.25)
    col = _mix3(valley_grass, soil, soil_mix * 0.62)
    col = _mix3(col, rock, steep_mix * 0.68 + high_mix * 0.40)

    if road_mix > 0.0:
        col = _mix3(col, road, road_mix)
    return col


def _base_height(x, y):
    xn = x / TERRAIN_SIZE
    yn = y / TERRAIN_SIZE

    h = 0.0
    h += math.sin(xn * 7.0 + 0.8) * math.cos(yn * 5.8 - 0.6) * 1.7
    h += math.sin(xn * 13.0 + 2.1) * math.cos(yn * 11.2 + 0.9) * 1.3
    h += math.sin(xn * 24.0 - 1.0) * math.sin(yn * 21.4 + 0.4) * 0.55

    for cx, cy, sigma, amp in _VALLEYS:
        h -= amp * _gaussian_2d(x, y, cx, cy, sigma)

    for cx, cy, sigma, amp in _HILLS:
        h += amp * _gaussian_2d(x, y, cx, cy, sigma)

    return h


def _apply_flatten_pads(x, y, h):
    specs = [
        SCENE_LAYOUT["plant_a"],
        SCENE_LAYOUT["plant_b"],
        SCENE_LAYOUT["building"],
        SCENE_LAYOUT["start_hub"],
    ]
    for spec in specs:
        cx, cy = spec["center"]
        hx, hy = spec["pad_half_extents"]
        nx = (x - cx) / max(1e-5, hx)
        ny = (y - cy) / max(1e-5, hy)
        d = math.sqrt(nx * nx + ny * ny)
        inner = _smoothstep(1.15, 0.80, d)
        if inner > 0.0:
            h = h * (1.0 - inner) + spec["floor_z"] * inner

        # Optional wider apron around a pad to reduce abrupt slopes nearby.
        sh = spec.get("surround_half_extents")
        if sh:
            shx, shy = sh
            snx = (x - cx) / max(1e-5, shx)
            sny = (y - cy) / max(1e-5, shy)
            sd = math.sqrt(snx * snx + sny * sny)
            surround = _smoothstep(1.28, 0.82, sd)
            if surround > 0.0:
                h = h * (1.0 - surround * 0.82) + spec["floor_z"] * (surround * 0.82)
    return h


def _apply_flatten_roads(x, y, h):
    road_width = SCENE_LAYOUT["roads"]["width"]
    feather = SCENE_LAYOUT["roads"]["feather"]

    best_dist = 1e9
    best_target = h
    for (p0, p1, z0, z1) in ROAD_SEGMENTS:
        dist, t = _dist_point_to_segment(x, y, p0[0], p0[1], p1[0], p1[1])
        if dist < best_dist:
            best_dist = dist
            best_target = z0 + (z1 - z0) * t

    blend = _smoothstep(feather, road_width, best_dist)
    if blend > 0.0:
        h = h * (1.0 - blend * 0.92) + best_target * (blend * 0.92)
    return h


def _build_heightmap():
    n = TILE_COUNT
    hmap = []
    for row in range(n):
        r = []
        y = (row / (n - 1)) * TERRAIN_SIZE - TERRAIN_SIZE / 2.0
        for col in range(n):
            x = (col / (n - 1)) * TERRAIN_SIZE - TERRAIN_SIZE / 2.0

            h = _base_height(x, y)
            h = _apply_flatten_pads(x, y, h)
            h = _apply_flatten_roads(x, y, h)
            r.append(h)
        hmap.append(r)
    return hmap


def _road_mask_strength(x, y):
    road_width = SCENE_LAYOUT["roads"]["width"]
    feather = SCENE_LAYOUT["roads"]["feather"]
    best_dist = 1e9
    for (p0, p1, _z0, _z1) in ROAD_SEGMENTS:
        dist, _ = _dist_point_to_segment(x, y, p0[0], p0[1], p1[0], p1[1])
        if dist < best_dist:
            best_dist = dist
    return _smoothstep(feather, road_width, best_dist)


def _build_geom(hmap):
    n = TILE_COUNT
    cell = TERRAIN_SIZE / (n - 1)
    off = TERRAIN_SIZE / 2.0

    fmt = GeomVertexFormat.get_v3n3c4()
    vdata = GeomVertexData("terrain", fmt, Geom.UHStatic)
    vdata.setNumRows(n * n)

    vwriter = GeomVertexWriter(vdata, "vertex")
    nwriter = GeomVertexWriter(vdata, "normal")
    cwriter = GeomVertexWriter(vdata, "color")

    for row in range(n):
        for col in range(n):
            h = hmap[row][col]
            x = col * cell - off
            y = row * cell - off
            vwriter.addData3(x, y, h)

            hr = hmap[row][min(col + 1, n - 1)]
            hl = hmap[row][max(col - 1, 0)]
            hu = hmap[min(row + 1, n - 1)][col]
            hd = hmap[max(row - 1, 0)][col]
            nx = (hl - hr) / (2 * cell)
            ny = (hd - hu) / (2 * cell)
            nz = 1.0
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            nwriter.addData3(nx / length, ny / length, nz / length)

            road_mix = _road_mask_strength(x, y)
            slope_mag = math.sqrt(nx * nx + ny * ny)
            tr, tg, tb = _terrain_color(x, y, h, slope_mag, road_mix)
            cwriter.addData4(tr, tg, tb, 1.0)

    tris = GeomTriangles(Geom.UHStatic)
    for row in range(n - 1):
        for col in range(n - 1):
            i = row * n + col
            tris.addVertices(i, i + 1, i + n)
            tris.addVertices(i + 1, i + n + 1, i + n)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode("terrain_geom")
    node.addGeom(geom)
    return node


class Terrain:
    def __init__(self, render, bullet_world):
        self._hmap = _build_heightmap()
        self._setup_visual(render)
        self._setup_physics(bullet_world)

    def _setup_visual(self, render):
        node = _build_geom(self._hmap)
        self.np = render.attachNewNode(node)

    def _setup_physics(self, bullet_world):
        n = TILE_COUNT
        flat = [self._hmap[row][col] for row in range(n) for col in range(n)]
        min_h = min(flat)
        max_h = max(flat)
        height_range = (max_h - min_h)

        img = PNMImage(n, n, 1)
        for row in range(n):
            for col in range(n):
                h = self._hmap[row][col]
                gray = (h - min_h) / (max_h - min_h) if max_h != min_h else 0.5
                img.setGray(col, n - 1 - row, gray)

        shape = BulletHeightfieldShape(img, height_range, ZUp)
        shape.setUseDiamondSubdivision(True)

        node = BulletRigidBodyNode("terrain_body")
        node.addShape(shape)
        node.setFriction(1.35)
        node.setRestitution(0.0)
        self.body_np = self.np.attachNewNode(node)

        xy_scale = TERRAIN_SIZE / (n - 1)
        self.body_np.setScale(xy_scale, xy_scale, 1.0)

        mid_h = (min_h + max_h) / 2.0
        self.body_np.setPos(0, 0, mid_h)

        bullet_world.attachRigidBody(node)

    def height_at(self, x, y):
        """Bilinear-interpolated terrain height at world position (x, y)."""
        n = TILE_COUNT
        cell = TERRAIN_SIZE / (n - 1)
        off = TERRAIN_SIZE / 2.0

        col_f = (x + off) / cell
        row_f = (y + off) / cell
        col0 = max(0, min(n - 2, int(col_f)))
        row0 = max(0, min(n - 2, int(row_f)))
        col1 = col0 + 1
        row1 = row0 + 1
        tc = col_f - col0
        tr = row_f - row0

        h00 = self._hmap[row0][col0]
        h01 = self._hmap[row0][col1]
        h10 = self._hmap[row1][col0]
        h11 = self._hmap[row1][col1]
        return (
            h00 * (1 - tc) * (1 - tr)
            + h01 * tc * (1 - tr)
            + h10 * (1 - tc) * tr
            + h11 * tc * tr
        )
