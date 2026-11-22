# -*- coding: utf-8 -*-
"""Report settlements that sit on water faces of the real map.txt, and how far
each was displaced from its historical longitude/latitude."""
import io, os, sys, math, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import roman_world as W
import historic as H

ROOT = os.path.dirname(HERE)


def load_map():
    lines = io.open(os.path.join(ROOT, "map.txt"), encoding="latin-1", newline="").read() \
        .replace("\r\n", "\n").split("\n")
    n = int(lines[0])
    V = [tuple(float(x) for x in l.split()) for l in lines[1:1 + n]]
    m = int(lines[1 + n])
    F = [l.split() for l in lines[2 + n:2 + n + m]]
    return V, F


def face_at(V, F, x, y):
    """terrain code of the face containing (x, y) plus its mean height"""
    for f in F:
        a, b, c = V[int(f[3])], V[int(f[4])], V[int(f[5])]
        (ax, ay), (bx, by), (cx, cy) = a[:2], b[:2], c[:2]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
        l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
        l3 = 1 - l1 - l2
        if l1 >= 0 and l2 >= 0 and l3 >= 0:
            return int(f[0]), (a[2] + b[2] + c[2]) / 3.0
    return None, None


def main():
    V, F = load_map()
    tables = {"p_town_": H.TOWNS, "p_castle_": H.CASTLES, "p_village_": H.VILLAGES}
    bad, far = [], []
    lines = io.open(os.path.join(ROOT, "parties.txt"), encoding="latin-1", newline="").read() \
        .replace("\r\n", "\n").split("\n")
    total = 0
    for line in lines:
        tk = line.split()
        if len(tk) < 20:
            continue
        for pref, tab in tables.items():
            if not tk[3].startswith(pref):
                continue
            idx = int(tk[3][len(pref):]) - 1
            if idx >= len(tab):
                continue
            name, lon, lat = tab[idx]
            x, y = float(tk[14]), float(tk[15])
            code, z = face_at(V, F, x, y)
            hx, hy = W.P(lon, lat)
            d = math.hypot(x - hx, y - hy)
            total += 1
            if code is None or code == 0 or code == 8:
                bad.append((tk[3], name, x, y, code, z))
            elif d > 6.0:
                far.append((tk[3], name, d, code, z))
    print("settlements checked:", total)
    print("ON WATER / NO FACE:", len(bad))
    for b in bad:
        print("   %-16s %-20s x=%8.2f y=%8.2f code=%s z=%s" % b)
    print("moved more than 6 map units from the historical point:", len(far))
    for b in sorted(far, key=lambda r: -r[2])[:30]:
        print("   %-16s %-20s moved %5.1f  code=%s z=%.2f" % (b[0], b[1], b[2], b[3], b[4]))


if __name__ == "__main__":
    main()
