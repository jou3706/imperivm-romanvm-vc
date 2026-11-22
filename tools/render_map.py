# -*- coding: utf-8 -*-
"""Rasterise the real map.txt (vertices + terrain faces) into a PNG for inspection."""
import zlib, struct, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODES = {0: (28, 74, 132), 1: (126, 118, 104), 2: (182, 162, 98), 3: (104, 140, 78),
         4: (234, 238, 242), 5: (214, 188, 120), 7: (150, 150, 120), 8: (140, 140, 110),
         10: (170, 160, 110), 11: (58, 104, 62), 12: (120, 130, 100), 13: (200, 180, 120)}


def main():
    path = os.path.join(ROOT, "map.txt")
    lines = open(path, encoding="latin-1", newline="").read().replace("\r\n", "\n").split("\n")
    n = int(lines[0])
    V = [tuple(float(x) for x in l.split()) for l in lines[1:1 + n]]
    m = int(lines[1 + n])
    F = [l.split() for l in lines[2 + n:2 + n + m]]
    # frame the whole Roman world (every settlement of parties.txt fits in here)
    X0, X1, YTOP, YBOT = -345.0, 285.0, 245.0, -240.0
    W = 760
    H = int(round(W * (YTOP - YBOT) / (X1 - X0)))
    px = bytearray(W * H * 3)
    def to_px(x, y):
        return (x - X0) * W / (X1 - X0), (YTOP - y) * H / (YTOP - YBOT)
    zmin = min(v[2] for v in V)
    zmax = max(v[2] for v in V)
    for f in F:
        col = CODES.get(int(f[0]), (255, 0, 255))
        a, b, c = V[int(f[3])], V[int(f[4])], V[int(f[5])]
        p = [to_px(*a[:2]), to_px(*b[:2]), to_px(*c[:2])]
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        x0, x1 = max(0, int(min(xs))), min(W - 1, int(max(xs)) + 1)
        y0, y1 = max(0, int(min(ys))), min(H - 1, int(max(ys)) + 1)
        (ax, ay), (bx, by), (cx, cy) = p
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        # hillshade from z
        z = (a[2] + b[2] + c[2]) / 3.0
        shade = 0.75 + 0.55 * (z - zmin) / max(0.001, zmax - zmin)
        colr = tuple(min(255, int(ch * shade)) for ch in col)
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                l1 = ((by - cy) * (xx + 0.5 - cx) + (cx - bx) * (yy + 0.5 - cy)) / den
                l2 = ((cy - ay) * (xx + 0.5 - cx) + (ax - cx) * (yy + 0.5 - cy)) / den
                l3 = 1 - l1 - l2
                if l1 >= -0.02 and l2 >= -0.02 and l3 >= -0.02:
                    o = (yy * W + xx) * 3
                    px[o:o + 3] = bytes(colr)
    # settlement dots
    import re
    pl = open(os.path.join(ROOT, "parties.txt"), encoding="latin-1", newline="").read().replace("\r\n", "\n").split("\n")
    for l in pl:
        tk = l.split()
        if len(tk) > 20 and re.match(r"p_(town|castle|village)_\d+$", tk[3]):
            x, y = float(tk[14]), float(tk[15])
            i, j = to_px(x, y)
            r = 3 if tk[3].startswith("p_town") else 1
            for dj in range(-r, r + 1):
                for di in range(-r, r + 1):
                    xx, yy = int(i) + di, int(j) + dj
                    if 0 <= xx < W and 0 <= yy < H:
                        o = (yy * W + xx) * 3
                        px[o:o + 3] = bytes((32, 0, 0)) if r == 3 else bytes((240, 224, 64))
    # special sites (caves, monasteries, mines, bridges, spawn points, ...)
    for l in pl:
        tk = l.split()
        if len(tk) > 20 and re.match(r"p_(?!town|castle|village)\w+$", tk[3]):
            x, y = float(tk[14]), float(tk[15])
            if x == 0 and y == 0:
                continue
            i, j = to_px(x, y)
            xx, yy = int(i), int(j)
            if 0 <= xx < W and 0 <= yy < H:
                o = (yy * W + xx) * 3
                px[o:o + 3] = bytes((240, 240, 255))
    rows = b"".join(b"\x00" + bytes(px[r * W * 3:(r + 1) * W * 3]) for r in range(H))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))
    out = os.path.join(ROOT, "tools", "map_from_file.png")
    open(out, "wb").write(png)
    print(out, "verts", n, "faces", m)


if __name__ == "__main__":
    main()
