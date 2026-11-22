# -*- coding: utf-8 -*-
"""Put the non-settlement parties of parties.txt back on solid ground.

The Roman map was rebuilt from real coastlines, but every special party (caves,
lairs, monasteries, mines, lumber camps, farms, quarries, bridges, ferries,
jetties, battle fields, training grounds, spawn points, map markers) still had
the coordinates of Viking Conquest's old map, so most of them ended up floating
in the Mediterranean.

Rules applied here:

* sites that should be inland (caves, monasteries, mines, camps, farms, ruins,
  arenas, player start) are moved inland, away from the coast, and kept apart
  from each other and from the settlements;
* coastal things (bridges, ferries, jetties, landing points, sea spawn points)
  are moved onto a shore, i.e. land that is at most COAST_WIDE units from the
  sea;
* the p_map_txt_* markers (invisible region markers, names are "{!}1") go back
  to the area their id names: Scotland, Northumbria, Wales, Cornwall, Wessex,
  East Anglia, Mercia, Ireland, Norway, Denmark, Frisia;
* runtime parties (temps, casualties, backups, the fleet) are left alone.

Every new position is checked against the real map triangles, so it never ends
on water, on a river face or on a bridge face.
"""
import io
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import coastline                     # noqa: E402
import roman_world as W              # noqa: E402

ROOT = os.path.dirname(HERE)

INLAND, COAST, LABEL, FIXED, SKIP = "inland", "coast", "label", "fixed", "skip"

# party ids that are runtime scratch parties: their coordinates are meaningless
RUNTIME = {
    "main_party_backup", "encountered_party_backup", "collective_friends_backup",
    "player_casualties", "enemy_casualties", "ally_casualties", "collective_enemy",
    "collective_ally", "collective_friends", "total_enemy_casualties",
    "routed_enemies", "camp_bandits", "yourlair", "followers_camp",
    "landing_point", "landing_point2", "the_fleet", "transporter",
    "troop_camp_1", "troop_camp_2", "reserved_1", "spawn_points_end",
    "temp_scene", "mega_danishrmy", "aescesdun",
}

COAST_WORDS = ("bridge", "ferry", "jetty", "spawn_point", "landing")

# the p_map_txt_* markers, in the order they appear, with their old region
LABELS = {
    "p_map_txt_laithlind": (-6.0, 57.0), "p_map_txt_alban": (-4.5, 57.3),
    "p_map_txt_altclut": (-4.5, 55.9), "p_map_txt_norphymbra_1": (-1.5, 54.5),
    "p_map_txt_norphymbra_2": (-2.5, 55.2), "p_map_txt_gwynedd_1": (-4.0, 53.0),
    "p_map_txt_gwynedd_2": (-3.2, 52.5), "p_map_txt_corniu_1": (-5.5, 50.2),
    "p_map_txt_corniu_2": (-4.3, 50.4), "p_map_txt_wessex": (-1.8, 51.0),
    "p_map_txt_eastengla": (0.8, 52.3), "p_map_txt_mearce": (-1.7, 52.6),
    "p_map_txt_aileach": (-7.5, 55.0), "p_map_txt_connachta": (-9.0, 53.5),
    "p_map_txt_meath": (-7.0, 53.6), "p_map_txt_laigin": (-6.9, 52.6),
    "p_map_txt_mumain": (-8.5, 51.8), "p_map_txt_noregr": (7.0, 60.0),
    "p_map_txt_danmork": (9.5, 56.0), "p_map_txt_frisa": (5.5, 53.2),
}

COAST_WIDE = 2.5        # a shore position is land this close to the sea
INLAND_MIN = 3.0        # inland positions keep at least this far from the sea
SITE_GAP = 6.0          # distance between two special sites
SETTLE_GAP = 1.5        # distance from a settlement


# ------------------------------------------------------------------ map faces
class Land(object):
    """Point-in-triangle queries against map.txt, bucketed on a coarse grid."""

    def __init__(self, root=ROOT, bucket=8.0):
        lines = io.open(os.path.join(root, "map.txt"), encoding="latin-1",
                        newline="").read().replace("\r\n", "\n").split("\n")
        n = int(lines[0])
        self.V = [tuple(float(x) for x in l.split()) for l in lines[1:1 + n]]
        m = int(lines[1 + n])
        self.F = [l.split() for l in lines[2 + n:2 + n + m]]
        self.bucket = bucket
        self.grid = {}
        for f in self.F:
            code = int(f[0])
            if code in (0, 7, 8):
                continue
            a, b, c = self.V[int(f[3])], self.V[int(f[4])], self.V[int(f[5])]
            if (a[2] + b[2] + c[2]) / 3.0 < 0.45:
                continue
            key = (int(math.floor(a[0] / bucket)), int(math.floor(a[1] / bucket)))
            for xx in range(int(math.floor(min(a[0], b[0], c[0]) / bucket)),
                            int(math.floor(max(a[0], b[0], c[0]) / bucket)) + 1):
                for yy in range(int(math.floor(min(a[1], b[1], c[1]) / bucket)),
                                int(math.floor(max(a[1], b[1], c[1]) / bucket)) + 1):
                    self.grid.setdefault((xx, yy), []).append(f)
        self._seen = {}

    def ok(self, x, y):
        key = (int(math.floor(x / self.bucket)), int(math.floor(y / self.bucket)))
        for f in self.grid.get(key, ()):
            a, b, c = self.V[int(f[3])], self.V[int(f[4])], self.V[int(f[5])]
            (ax, ay), (bx, by), (cx, cy) = a[:2], b[:2], c[:2]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9:
                continue
            l1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
            l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
            l3 = 1 - l1 - l2
            if l1 >= 0 and l2 >= 0 and l3 >= 0:
                return True
        return False


# ------------------------------------------------------------------ placement
def classify(pid):
    short = pid[2:]
    if pid.startswith(("p_town", "p_castle", "p_village")):
        return SKIP
    if short.startswith("temp") or short in RUNTIME:
        return SKIP
    if pid == "p_main_party":
        return FIXED
    if pid in LABELS:
        return LABEL
    if any(w in short for w in COAST_WORDS):
        return COAST
    return INLAND


def fits(land, x, y, kind, placed, settle, settle_gap):
    if not (-330.0 < x < 270.0 and -230.0 < y < 235.0):
        return False
    if not land.ok(x, y) or not coastline.is_land(x, y):
        return False
    sd = coastline.land_sd(x, y)
    if kind == COAST:
        if sd <= 0.0 or sd > COAST_WIDE:
            return False
    elif sd < INLAND_MIN:
        return False
    for (sx, sy) in settle:
        if (sx - x) ** 2 + (sy - y) ** 2 < settle_gap ** 2:
            return False
    for (px, py) in placed:
        if (px - x) ** 2 + (py - y) ** 2 < SITE_GAP ** 2:
            return False
    return True


def find_spot(land, pid, kind, placed, settle, rng, start=None):
    """Ring search outwards from start (or from a random point), then random."""
    base_x, base_y = start if start else (rng.uniform(-320, 260), rng.uniform(-220, 225))
    for radius in (3.0, 6.0, 10.0, 15.0, 22.0, 30.0, 40.0, 55.0):
        for k in range(28):
            ang = (k / 28.0) * 2 * math.pi + rng.random() * 0.2
            x = base_x + radius * math.cos(ang)
            y = base_y + radius * math.sin(ang)
            if fits(land, x, y, kind, placed, settle, SETTLE_GAP):
                return x, y
    for _ in range(30000):
        x = rng.uniform(-320.0, 260.0)
        y = rng.uniform(-215.0, 225.0)
        if fits(land, x, y, kind, placed, settle, SETTLE_GAP):
            return x, y
    raise RuntimeError("no free spot for %s" % pid)


def main(seed=20261122):
    rng = random.Random(seed)
    land = Land()
    path = os.path.join(ROOT, "parties.txt")
    raw = io.open(path, encoding="latin-1", newline="").read()
    crlf = "\r\n" in raw
    lines = raw.replace("\r\n", "\n").split("\n")

    settle = []
    for line in lines:
        tk = line.split()
        if len(tk) > 20 and tk[3].startswith(("p_town", "p_castle", "p_village")):
            settle.append((float(tk[14]), float(tk[15])))

    placed = []
    moved = {INLAND: 0, COAST: 0, LABEL: 0, FIXED: 0}
    for i, line in enumerate(lines):
        tk = line.split()
        if len(tk) < 21 or not tk[3].startswith("p_"):
            continue
        pid = tk[3]
        kind = classify(pid)
        if kind in (SKIP,):
            continue
        x, y = float(tk[14]), float(tk[15])
        if kind == LABEL:
            lon, lat = LABELS[pid]
            x, y = W.P(lon, lat)
            if not (land.ok(x, y) and coastline.is_land(x, y)
                    and coastline.land_sd(x, y) >= 1.0):
                x, y = find_spot(land, pid, INLAND, placed, settle, rng, (x, y))
        elif kind == FIXED:      # the player starts next to Roma
            x, y = W.P(12.5, 41.9)
            x += 2.5
            y += 2.5
            x, y = find_spot(land, pid, INLAND, placed, settle, rng, (x, y))
        elif coastline.is_land(x, y) and land.ok(x, y):
            # already on solid ground: keep the spot, it only needs to be spaced
            if coastline.land_sd(x, y) >= (INLAND_MIN if kind == INLAND else 0.5):
                placed.append((x, y))
                continue
            x, y = find_spot(land, pid, kind, placed, settle, rng, (x, y))
        else:
            x, y = find_spot(land, pid, kind, placed, settle, rng, (x, y))

        for n in range(3):
            tk[14 + 2 * n] = "%.6f" % x
            tk[15 + 2 * n] = "%.6f" % y
        lead = line[:len(line) - len(line.lstrip())]
        trail = line[len(line.rstrip()):]
        lines[i] = lead + " ".join(tk) + trail
        placed.append((x, y))
        moved[kind] += 1

    out = "\n".join(lines)
    if crlf:
        out = out.replace("\n", "\r\n")
    io.open(path, "w", encoding="latin-1", newline="").write(out)
    print("moved:", moved, "total sites placed:", len(placed))


if __name__ == "__main__":
    main()
