"""Height / terrain sampler for the Roman world, plus a PNG preview renderer."""
import math, zlib, struct
import roman_world as W
import coastline

# ---------------------------------------------------------------- helpers
def _in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside

def _seg_dist(x, y, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    if L <= 1e-12:
        return math.hypot(x - x0, y - y0)
    t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L))
    return math.hypot(x - (x0 + t * dx), y - (y0 + t * dy))

def _poly_sd(x, y, poly):
    d = min(_seg_dist(x, y, poly[i][0], poly[i][1], poly[(i + 1) % len(poly)][0], poly[(i + 1) % len(poly)][1])
            for i in range(len(poly)))
    return d if _in_poly(x, y, poly) else -d

def _hash(ix, iy, seed=0):
    h = (ix * 374761393 + iy * 668265263 + seed * 1442695040) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0

def _vnoise(x, y, seed=0):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, seed); b = _hash(ix + 1, iy, seed)
    c = _hash(ix, iy + 1, seed); d = _hash(ix + 1, iy + 1, seed)
    return (a * (1 - sx) + b * sx) * (1 - sy) + (c * (1 - sx) + d * sx) * sy

def fbm(x, y, seed=0, oct=4, freq=0.055):
    v, amp, f = 0.0, 1.0, freq
    tot = 0.0
    for o in range(oct):
        v += amp * _vnoise(x * f, y * f, seed + o * 17)
        tot += amp
        amp *= 0.5
        f *= 2.0
    return v / tot

# ---------------------------------------------------------------- sampling
_BB = {n: (min(p[0] for p in poly), min(p[1] for p in poly),
            max(p[0] for p in poly), max(p[1] for p in poly))
       for n, poly in W.LAND.items()}

def land_sd(x, y):
    """Signed distance to the real coastline (positive inland), map units.

    The hand-written roman_world.LAND polygons are no longer used for the
    shape of the sea: coastline.py holds Natural Earth's 1:10m land data.
    """
    return coastline.land_sd(x, y)

def ridge_boost(x, y):
    h = 0.0
    for (x0, y0, x1, y1, r, hh) in W.RIDGES:
        d = _seg_dist(x, y, x0, y0, x1, y1)
        if d < r:
            t = 1.0 - d / r
            h = max(h, hh * (t ** 1.5))
    return h

# Warband draws the sea surface where the water faces are, and both Native and
# Viking Conquest keep every water vertex exactly on the water line (Native: 0.0,
# VC: ~0.9).  Our first build put the sea *below* zero and dropped a 2+ unit wall
# at every beach; that is what showed up as black water/edges in game.
SEA_LEVEL = 0.0


def height(x, y):
    _lon, lat = lonlat(x, y)
    sd = land_sd(x, y) + (fbm(x, y, seed=7, freq=0.11) - 0.5) * 3.2
    if sd <= 0:
        return SEA_LEVEL
    n = fbm(x, y, seed=3)
    t = min(1.0, sd / 9.0)
    top = (1.0 - t) ** 0.8
    # the shore starts just above the water line, so coasts are beaches and not cliffs
    h = 0.35 + 2.9 * t + 0.55 * top
    h += (n - 0.5) * 1.5
    h += ridge_boost(x, y) * (0.55 + 0.9 * fbm(x * 1.7, y * 1.7, seed=23))
    # deserts and steppes are flatter, high latitudes slightly higher
    if lat < 30.0:
        h = h * 0.55 + 0.15
    if lat > 49.0:
        h += 0.6 * (lat - 49.0) / 6.0
    return max(0.16, min(15.8, h))

def lonlat(x, y):
    return x / W.SX + W.X0, y / W.SY + W.Y0

def terrain(x, y, z):
    if z < 0.06:
        return 0                    # water
    if z > 5.8:
        return 1                    # mountains
    lon, lat = lonlat(x, y)
    if lat > 56.5:
        return 4                    # snow (far north only)
    nile = 29.2 < lon < 32.7 and lat < 31.6
    # VC only uses terrain code 5 (desert) on 60 faces of its own map, and the
    # engine has no desert map material in the module: those faces came out black.
    # Code 2 (steppe) is what Da/VC land uses for dry open country and renders
    # with VC's own map_steppe texture.
    if lat < 30.6 + 1.4 * fbm(x, y, seed=61, freq=0.03) and not nile:
        return 2                    # Sahara / Libya / Sinai (dry steppe)
    if lat < 33.2 and 34.0 < lon < 42.0 and fbm(x, y, seed=41, freq=0.07) > 0.45:
        return 2                    # Syrian / Arabian desert (dry steppe)
    if lat > 44.0 and lon > 33.0 and fbm(x, y, seed=53, freq=0.06) > 0.40:
        return 2                    # Scythian steppe north of the Black Sea
    if fbm(x, y, seed=11, freq=0.09) > 0.64 and z < 5.0:
        return 11                   # forest
    return 3                        # plains / grass

# ---------------------------------------------------------------- preview
CODE_COL = {
    0: (26, 70, 128), 1: (120, 112, 100), 2: (176, 158, 96), 3: (104, 140, 78),
    4: (232, 236, 240), 5: (216, 190, 120), 11: (58, 104, 62),
}

def render(path, width=480, hpx=386, parties=None):
    px = []
    for j in range(hpx):
        row = bytearray()
        y = 145 - (j + 0.5) * 290.0 / hpx
        for i in range(width):
            x = -180 + (i + 0.5) * 360.0 / width
            z = height(x, y)
            c = CODE_COL[terrain(x, y, z)]
            shade = 1.0 + (z - 2.0) * 0.035
            if z < 0.06:
                shade = 0.85 + 0.15 * min(1.0, (145 - abs(y)) / 145.0)
            row += bytes(int(max(0, min(255, ch * shade))) for ch in c)
        px.append(row)
    if parties:
        for (x, y, col) in parties:
            i = int((x + 180) * width / 360.0)
            j = int((145 - y) * hpx / 290.0)
            for dj in range(-2, 3):
                for di in range(-2, 3):
                    if 0 <= j + dj < hpx and 0 <= i + di < width:
                        px[j + dj][(i + di) * 3:(i + di) * 3 + 3] = bytes(col)
    raw = b"".join(b"\x00" + bytes(r) for r in px)
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, hpx, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    open(path, "wb").write(png)
    return path

if __name__ == "__main__":
    print(render("tools/world_preview.png"))
