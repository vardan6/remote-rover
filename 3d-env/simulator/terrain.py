from panda3d.core import (
    GeomNode, Geom, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexWriter, PNMImage
)
from panda3d.bullet import BulletRigidBodyNode, BulletHeightfieldShape, ZUp
import json
import math
from pathlib import Path


SCENE_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "terrain_scene.v1.json"


def _to_tuples(value):
    if isinstance(value, list):
        return tuple(_to_tuples(item) for item in value)
    if isinstance(value, dict):
        return {key: _to_tuples(item) for key, item in value.items()}
    return value


def _load_scene_config():
    with SCENE_CONFIG_PATH.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return _to_tuples(payload)


SCENE_MANIFEST = _load_scene_config()
TERRAIN_SIZE = int(SCENE_MANIFEST["terrain"]["size"][0])
TILE_COUNT = int(SCENE_MANIFEST["terrain"]["tile_count"])
SCENE_OBJECTS = SCENE_MANIFEST["objects"]
SPAWN_POINTS = SCENE_MANIFEST["spawn_points"]
SCENE_ROADS = SCENE_MANIFEST["roads"]
SCENE_GEOREFERENCE = SCENE_MANIFEST.get("coordinate_system", {}).get("georeference", {})


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


def _build_heightmap():
    return [list(row) for row in SCENE_MANIFEST["terrain"]["heightfield"]]


def _road_mask_strength(x, y):
    best_mix = 0.0
    for road in SCENE_ROADS:
        p0, p1 = road["centerline"]
        dist, _ = _dist_point_to_segment(x, y, p0[0], p0[1], p1[0], p1[1])
        geom = road["geometry"]
        best_mix = max(best_mix, _smoothstep(geom["feather"], geom["width"], dist))
    return best_mix


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
