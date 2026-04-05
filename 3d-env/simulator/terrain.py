from panda3d.core import (
    NodePath, GeomNode, Geom, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexWriter, Vec3, LColor, PNMImage
)
from panda3d.bullet import BulletRigidBodyNode, BulletHeightfieldShape, ZUp
import random
import math


TERRAIN_SIZE = 200   # world units (2x larger than before)
TILE_COUNT   = 160   # vertices per side; doubled to keep terrain detail density


def _build_heightmap():
    """Multi-octave heightmap with hills, valleys, and surface roughness.

    Terrain heights are in metres; positive = above origin, negative = valley.
    Octave breakdown:
      - Broad hills   : ±0.45 m amplitude, long wavelength
      - Large hills   : ±1.95 m amplitude, ~30% denser than before
      - Medium rolls  : ±0.72 m amplitude, ~30% denser than before
      - Fine roughness: ±0.20 m amplitude, ~30% denser than before
    """
    n = TILE_COUNT
    hmap = []
    for row in range(n):
        r = []
        for col in range(n):
            x = col / (n - 1)   # [0, 1]
            y = row / (n - 1)   # [0, 1]
            # Extra broad variation + denser octaves for richer terrain shape.
            h  = math.sin(x * 2.3 + 2.2) * math.cos(y * 2.0 + 1.5) * 0.45
            h += math.sin(x * 5.2 + 0.5) * math.cos(y * 4.6 + 0.7) * 1.95
            h += math.sin(x * 10.4 + 1.1) * math.sin(y * 9.1 + 0.3) * 0.72
            h += math.sin(x * 20.8 + 0.7) * math.cos(y * 18.2 + 1.4) * 0.20
            r.append(h)
        hmap.append(r)
    return hmap


def _build_geom(hmap):
    n    = TILE_COUNT
    cell = TERRAIN_SIZE / (n - 1)
    off  = TERRAIN_SIZE / 2.0

    fmt   = GeomVertexFormat.get_v3n3c4()
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

            # Approximate surface normal via central finite differences
            hr = hmap[row][min(col + 1, n - 1)]
            hl = hmap[row][max(col - 1, 0)]
            hu = hmap[min(row + 1, n - 1)][col]
            hd = hmap[max(row - 1, 0)][col]
            nx = (hl - hr) / (2 * cell)
            ny = (hd - hu) / (2 * cell)
            nz = 1.0
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            nwriter.addData3(nx / length, ny / length, nz / length)

            # Checkerboard pattern (8-tile period) so movement is obvious
            checker = (row // 8 + col // 8) % 2
            if checker:
                cwriter.addData4(0.55, 0.42, 0.22, 1.0)   # tan / sandy
            else:
                cwriter.addData4(0.28, 0.52, 0.18, 1.0)   # green

    tris = GeomTriangles(Geom.UHStatic)
    for row in range(n - 1):
        for col in range(n - 1):
            i = row * n + col
            tris.addVertices(i,     i + 1, i + n)
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
        self.np.setTwoSided(True)

    def _setup_physics(self, bullet_world):
        n    = TILE_COUNT
        flat = [self._hmap[row][col] for row in range(n) for col in range(n)]
        min_h = min(flat)
        max_h = max(flat)
        height_range = (max_h - min_h)

        # BulletHeightfieldShape: grayscale [0,1] is mapped into the provided
        # full vertical range and centred around shape-local Z=0.
        img = PNMImage(n, n, 1)
        for row in range(n):
            for col in range(n):
                h    = self._hmap[row][col]
                gray = (h - min_h) / (max_h - min_h) if max_h != min_h else 0.5
                img.setGray(col, n - 1 - row, gray)

        # IMPORTANT: Bullet expects the FULL height range here, not half-range.
        # Using half-range compresses collision terrain vertically and makes the
        # rover appear to hover or tilt against a different "plane" than visuals.
        shape = BulletHeightfieldShape(img, height_range, ZUp)
        shape.setUseDiamondSubdivision(True)

        node = BulletRigidBodyNode("terrain_body")
        node.addShape(shape)
        self.body_np = self.np.attachNewNode(node)

        # Scale pixel coords → world units
        xy_scale = TERRAIN_SIZE / (n - 1)
        self.body_np.setScale(xy_scale, xy_scale, 1.0)

        # Bullet centres the generated heightfield about Z=0, so shift by the
        # midpoint of our source heights to align physics and visual terrain.
        mid_h = (min_h + max_h) / 2.0
        self.body_np.setPos(0, 0, mid_h)

        bullet_world.attachRigidBody(node)

    def height_at(self, x, y):
        """Bilinear-interpolated terrain height at world position (x, y)."""
        n    = TILE_COUNT
        cell = TERRAIN_SIZE / (n - 1)
        off  = TERRAIN_SIZE / 2.0

        col_f = (x + off) / cell
        row_f = (y + off) / cell
        col0 = max(0, min(n - 2, int(col_f)))
        row0 = max(0, min(n - 2, int(row_f)))
        col1 = col0 + 1
        row1 = row0 + 1
        tc   = col_f - col0
        tr   = row_f - row0

        h00 = self._hmap[row0][col0]
        h01 = self._hmap[row0][col1]
        h10 = self._hmap[row1][col0]
        h11 = self._hmap[row1][col1]
        return (h00 * (1 - tc) * (1 - tr) + h01 * tc * (1 - tr) +
                h10 * (1 - tc) * tr       + h11 * tc * tr)
