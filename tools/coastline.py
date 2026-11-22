# -*- coding: utf-8 -*-
"""Real coastline for the Roman map: Natural Earth 1:10m land polygons.

The old roman_world.LAND polygons had 15-30 hand written points per landmass,
which is why bays, peninsulas and islands kept disagreeing with the settlements
that sit on them.  This module throws that away and uses Natural Earth's public
domain 1:10m land data (roughly 1.4 km accuracy) instead:

* every land polygon is projected with roman_world.P() into map units
* the result is rasterised into a grid of CELL (0.5) map units per cell
* a signed distance field is computed from it (positive inland, negative at sea)

so the rest of the pipeline only ever asks for `land_sd(x, y)` / `is_land(x, y)`
and never touches polygons again.  The field is cached next to the source data,
so rebuilding the map afterwards takes a second instead of ~30 s.
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw

import roman_world as W

HERE = os.path.dirname(os.path.abspath(__file__))

CELL = 0.5                        # map units per grid cell (1 unit ~ 8 km)
XMIN, YMIN = -432.0, -432.0
XMAX, YMAX = 432.0, 432.0
NX = int(round((XMAX - XMIN) / CELL))
NY = int(round((YMAX - YMIN) / CELL))
SS = 2                            # supersampling factor for the rasteriser
GEOJSON_NAME = "ne_10m_land.geojson"
CACHE_NAME = "coast_field.npz"

INF = 1e12
_LAND = None
_SD = None


# --------------------------------------------------------------- source data
def _data_dir():
    """Where ne_10m_land.geojson lives (shared between the two module copies)."""
    cands = [
        os.path.join(HERE, "data"),
        os.path.join(HERE, "..", "..", "Native Tactical", "tools", "data"),
        os.path.join(HERE, "..", "..", "Imperivm Romanvm VC", "tools", "data"),
    ]
    for c in cands:
        c = os.path.abspath(c)
        if os.path.exists(os.path.join(c, GEOJSON_NAME)):
            return c
    raise IOError("%s not found - run tools/fetch_coastline.py" % GEOJSON_NAME)


def _rings():
    """All land rings, exterior first followed by holes, projected to map units."""
    with open(os.path.join(_data_dir(), GEOJSON_NAME), encoding="utf-8") as fh:
        gj = json.load(fh)
    out = []
    for feat in gj.get("features", []):
        g = feat.get("geometry") or {}
        t = g.get("type")
        if t == "Polygon":
            polys = [g["coordinates"]]
        elif t == "MultiPolygon":
            polys = g["coordinates"]
        else:
            continue
        for poly in polys:
            rings = []
            for ring in poly:
                a = np.asarray(ring, dtype=np.float64)
                if a.shape[0] < 3:
                    continue
                xs = (a[:, 0] - W.X0) * W.SX
                ys = (a[:, 1] - W.Y0) * W.SY
                if xs.max() < XMIN - 40 or xs.min() > XMAX + 40:
                    continue
                if ys.max() < YMIN - 40 or ys.min() > YMAX + 40:
                    continue
                rings.append(np.column_stack([xs, ys]))
            if rings:
                out.append(rings)
    return out


# Islands that matter historically but are smaller than one mesh face (~3.5 map
# units) in 1:10m data: they are stamped explicitly so a face can hold them.
# (lon, lat, radius in map units)
_PATCHES = [
    (14.45, 35.90, 4.6),      # Melita / Malta (mesh faces are ~3.5 units wide)
]


# ------------------------------------------------------------------ rasterise
def _raster():
    img = Image.new("L", (NX * SS, NY * SS), 0)
    dr = ImageDraw.Draw(img)
    for rings in _rings():
        for k, ring in enumerate(rings):
            xs = (ring[:, 0] - XMIN) / CELL * SS
            ys = (YMAX - ring[:, 1]) / CELL * SS
            dr.polygon(list(zip(xs.tolist(), ys.tolist())), fill=255 if k == 0 else 0)
    for lon, lat, r in _PATCHES:
        x, y = W.P(lon, lat)
        cx = (x - XMIN) / CELL * SS
        cy = (YMAX - y) / CELL * SS
        rr = r / CELL * SS
        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=255)
    img = img.resize((NX, NY), Image.BOX)
    return np.asarray(img, dtype=np.float64) >= 90.0


# ------------------------------------------------------- exact 1-D distance
def _edt1d(f):
    """Felzenszwalb & Huttenlocher squared distance transform of one line."""
    n = f.size
    v = np.empty(n, dtype=np.int64)
    z = np.empty(n + 1)
    d = np.empty(n)
    k = 0
    v[0] = 0
    z[0] = -np.inf
    z[1] = np.inf
    for q in range(1, n):
        fq = f[q] + q * q
        while True:
            p = v[k]
            s = (fq - (f[p] + p * p)) / (2.0 * (q - p))
            if s <= z[k] and k > 0:
                k -= 1
                continue
            break
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = np.inf
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        dv = q - v[k]
        d[q] = dv * dv + f[v[k]]
    return d


def _edt2d(f):
    out = f.copy()
    for i in range(out.shape[0]):
        out[i] = _edt1d(out[i])
    for j in range(out.shape[1]):
        out[:, j] = _edt1d(out[:, j])
    return out


# -------------------------------------------------------------------- field
def _build():
    land = _raster()
    # zeros mark the features, so: zeros at sea -> distance to the sea (inland),
    # zeros on land -> distance to land (out at sea).
    inland = np.sqrt(_edt2d(np.where(land, INF, 0.0)))
    offshore = np.sqrt(_edt2d(np.where(land, 0.0, INF)))
    sd = np.where(land, inland, -offshore) * CELL
    return land, sd.astype(np.float32)


def load(rebuild=False):
    global _LAND, _SD
    if _LAND is not None and not rebuild:
        return _LAND, _SD
    path = os.path.join(_data_dir(), CACHE_NAME)
    if not rebuild and os.path.exists(path):
        try:
            z = np.load(path)
            if z["sd"].shape == (NY, NX):
                _LAND, _SD = z["land"], z["sd"]
                return _LAND, _SD
        except Exception:
            pass
    land, sd = _build()
    try:
        np.savez_compressed(path, land=land, sd=sd)
    except Exception:
        pass
    _LAND, _SD = land, sd
    return _LAND, _SD


def _sample(field, x, y):
    fx = np.clip((np.asarray(x, dtype=np.float64) - XMIN) / CELL - 0.5, 0, NX - 1.001)
    fy = np.clip((YMAX - np.asarray(y, dtype=np.float64)) / CELL - 0.5, 0, NY - 1.001)
    i = fx.astype(np.int64)
    j = fy.astype(np.int64)
    tx = fx - i
    ty = fy - j
    row0 = field[j, i] * (1 - tx) + field[j, i + 1] * tx
    row1 = field[j + 1, i] * (1 - tx) + field[j + 1, i + 1] * tx
    return row0 * (1 - ty) + row1 * ty


def _scalar(v):
    return float(v) if np.ndim(v) == 0 else v


def land_sd(x, y):
    """Signed distance to the real coastline in map units (positive inland)."""
    load()
    return _scalar(_sample(_SD, x, y))


def is_land(x, y):
    """True where the rasterised land mask covers the point."""
    load()
    return _scalar(_sample(_LAND.astype(np.float32), x, y) >= 0.5)


def coverage():
    load()
    return float(_LAND.mean())


if __name__ == "__main__":
    land, sd = load(rebuild=True)
    print("grid %dx%d  cell %.2f units  land %.1f%%  sd %.1f..%.1f"
          % (NX, NY, CELL, 100.0 * land.mean(), float(sd.min()), float(sd.max())))
    out = os.path.join(HERE, "coast_preview.png")
    Image.fromarray((land * 255).astype(np.uint8)).convert("L").resize(
        (NX // 2, NY // 2), Image.BOX).save(out)
    print(out)
