# -*- coding: utf-8 -*-
"""Historical gazetteer: real Roman-era places with real lon/lat.

Each settlement slot in parties.txt gets a historically correct name and a
position computed from its real coordinates through roman_world.P().
"""
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import roman_mapgen as M  # noqa: E402
import roman_world as W  # noqa: E402

# (name, lon, lat) -- 29 provincial capitals / great cities
TOWNS = [
    ("Roma", 12.50, 41.90), ("Carthago", 10.32, 36.85), ("Alexandria", 29.92, 31.20),
    ("Antiochia", 36.16, 36.20), ("Ephesus", 27.34, 37.94), ("Corinthus", 22.93, 37.94),
    ("Athenae", 23.73, 37.98), ("Massilia", 5.37, 43.30), ("Narbo", 3.00, 43.18),
    ("Tarraco", 1.25, 41.12), ("Carthago_Nova", -0.98, 37.60), ("Gades", -6.29, 36.53),
    ("Caesaraugusta", -0.88, 41.65), ("Lugdunum", 4.83, 45.76), ("Londinium", -0.13, 51.51),
    ("Camulodunum", 0.90, 51.89), ("Eboracum", -1.08, 53.96), ("Mediolanum", 9.19, 45.46),
    ("Ravenna", 12.28, 44.42), ("Aquileia", 13.37, 45.77), ("Byzantium", 28.98, 41.01),
    ("Thessalonica", 22.94, 40.64), ("Pergamum", 27.18, 39.12), ("Smyrna", 27.14, 38.42),
    ("Caesarea_Maritima", 34.89, 32.50), ("Tarsus", 34.90, 36.92), ("Cyrene", 21.86, 32.82),
    ("Syracusae", 15.29, 37.07), ("Leptis_Magna", 14.29, 32.64),
]

# (name, lon, lat) -- 90 secondary cities, legionary fortresses, bishoprics
CASTLES = [
    ("Ostia", 12.29, 41.75), ("Puteoli", 14.12, 40.83), ("Capua", 14.25, 41.08),
    ("Neapolis", 14.25, 40.85), ("Brundisium", 17.94, 40.64), ("Tarentum", 17.24, 40.47),
    ("Croton", 17.13, 39.08), ("Rhegium", 15.65, 38.11), ("Messana", 15.55, 38.19),
    ("Panormus", 13.36, 38.12), ("Lilybaeum", 12.43, 37.80), ("Agrigentum", 13.58, 37.31),
    ("Catina", 15.09, 37.50), ("Genua", 8.93, 44.41), ("Pisae", 10.40, 43.72),
    ("Florentia", 11.25, 43.77), ("Arretium", 11.88, 43.46), ("Perusia", 12.39, 43.11),
    ("Ariminum", 12.57, 44.06), ("Ancona", 13.51, 43.62), ("Barium", 16.87, 41.13),
    ("Verona", 10.99, 45.44), ("Patavium", 11.88, 45.41), ("Brixia", 10.22, 45.54),
    ("Cremona", 10.02, 45.13), ("Parma", 10.33, 44.80), ("Mutina", 10.93, 44.65),
    ("Bononia", 11.34, 44.49), ("Placentia", 9.69, 45.05), ("Ticinum", 9.16, 45.19),
    ("Augusta_Taurinorum", 7.69, 45.07), ("Alba_Pompeia", 8.03, 44.70), ("Nemausus", 4.36, 43.84),
    ("Arelate", 4.63, 43.68), ("Avennio", 4.81, 43.95), ("Vienna", 4.87, 45.52),
    ("Tolosa", 1.44, 43.60), ("Burdigala", -0.58, 44.84), ("Agatha", 3.47, 43.31),
    ("Baeterrae", 3.22, 43.34), ("Forum_Julii", 6.64, 43.43), ("Antipolis", 7.13, 43.58),
    ("Cemenelum", 7.27, 43.72), ("Aleria", 9.51, 42.11), ("Caralis", 9.11, 39.22),
    ("Turris_Libisonis", 8.40, 40.85), ("Olbia", 9.50, 40.92), ("Tharros", 8.44, 39.87),
    ("Melita", 14.51, 35.90), ("Utica", 10.05, 37.06), ("Hippo_Regius", 7.77, 36.90),
    ("Hadrumetum", 10.64, 35.83), ("Leptis_Minor", 10.90, 35.60), ("Thysdrus", 10.71, 35.30),
    ("Tacape", 10.10, 33.88), ("Oea", 13.18, 32.90), ("Sabratha", 12.49, 32.79),
    ("Berenice", 20.07, 32.12), ("Ptolemais", 20.95, 32.70), ("Paraetonium", 25.15, 31.35),
    ("Pelusium", 32.60, 31.05), ("Memphis", 31.25, 29.85), ("Coptos", 32.82, 26.00),
    ("Thebae", 32.65, 25.70), ("Myos_Hormos", 34.24, 26.15), ("Gaza", 34.45, 31.50),
    ("Ascalon", 34.55, 31.67), ("Jamnia", 34.75, 31.93), ("Dora", 34.92, 32.62),
    ("Ptolemais_Ace", 35.07, 32.92), ("Tyros", 35.20, 33.27), ("Sidon", 35.37, 33.56),
    ("Berytus", 35.50, 33.89), ("Tripolis", 35.84, 34.44), ("Aradus", 35.86, 34.86),
    ("Laodicea", 35.78, 35.52), ("Seleucia_Pieria", 35.93, 36.12), ("Adana", 35.32, 37.00),
    ("Anazarbus", 35.90, 37.24), ("Mopsuestia", 35.63, 36.96), ("Cyrrhus", 36.75, 36.74),
    ("Zeugma", 37.87, 37.06), ("Edessa", 38.79, 37.15), ("Carrhae", 39.03, 36.86),
    ("Nisibis", 41.20, 37.07), ("Dura_Europos", 40.73, 34.75), ("Palmyra", 38.27, 34.55),
    ("Damascus", 36.29, 33.51), ("Bostra", 36.48, 32.52), ("Petra", 35.44, 30.33),
]

# (name, lon, lat) -- 150 towns, vici, road stations
VILLAGES = [
    # Italy
    ("Veii", 12.40, 42.02), ("Falerii", 12.35, 42.30), ("Sutrium", 12.22, 42.24),
    ("Tarquinii", 11.90, 42.25), ("Caere", 12.10, 42.00), ("Alba_Fucens", 13.53, 42.10),
    ("Corfinium", 13.83, 42.12), ("Beneventum", 14.78, 41.13), ("Aeculanum", 15.05, 40.98),
    ("Venusia", 15.82, 40.96), ("Canusium", 16.06, 41.22), ("Luceria", 15.33, 41.51),
    ("Sipontum", 15.90, 41.60), ("Arpi", 15.70, 41.50), ("Hydruntum", 18.35, 40.15),
    ("Lupiae", 18.17, 40.35), ("Thurii", 16.55, 39.72), ("Vibo_Valentia", 16.10, 38.68),
    ("Locri", 16.26, 38.24), ("Consentia", 16.25, 39.30), ("Paestum", 14.99, 40.42),
    ("Velia", 15.16, 40.16), ("Cumae", 14.05, 40.85), ("Minturnae", 13.77, 41.24),
    ("Formiae", 13.61, 41.26), ("Terracina", 13.24, 41.29), ("Antium", 12.63, 41.45),
    ("Tusculum", 12.71, 41.80), ("Praeneste", 12.83, 41.96), ("Tibur", 12.80, 42.00),
    ("Volsinii", 11.99, 42.65), ("Clusium", 11.95, 43.02), ("Cortona", 11.99, 43.27),
    ("Faesulae", 11.30, 43.80), ("Luca", 10.50, 43.84), ("Luna", 10.02, 44.06),
    ("Volaterrae", 10.86, 43.40), ("Populonia", 10.49, 42.99), ("Centumcellae", 11.79, 42.09),
    ("Aquinum", 13.70, 41.49), ("Casinum", 13.83, 41.49), ("Venafrum", 14.05, 41.48),
    ("Saepinum", 14.60, 41.43), ("Aesernia", 14.23, 41.60), ("Teanum", 14.06, 41.25),
    ("Nola", 14.53, 40.93), ("Nuceria", 14.67, 40.75), ("Salernum", 14.77, 40.68),
    ("Grumentum", 15.90, 40.28), ("Heraclea", 16.68, 40.22), ("Metapontum", 16.82, 40.38),
    ("Scylletium", 16.63, 38.80), ("Caulonia", 16.60, 38.35), ("Tauromenium", 15.29, 37.85),
    ("Tyndaris", 15.05, 38.15), ("Cephaloedium", 14.03, 37.99), ("Himera", 13.72, 37.98),
    ("Soluntum", 13.53, 38.09), ("Segesta", 12.84, 37.94), ("Eryx", 12.59, 38.04),
    ("Drepanum", 12.50, 38.02), ("Selinus", 12.60, 37.58), ("Heraclea_Minoa", 13.10, 37.39),
    ("Gela", 14.25, 37.07), ("Camarina", 14.44, 36.87), ("Netum", 14.93, 36.94),
    ("Megara_Hybaea", 15.18, 37.20), ("Leontini", 14.99, 37.31),
    # Greece
    ("Sparta", 22.43, 37.08), ("Argos", 22.73, 37.63), ("Tegea", 22.42, 37.45),
    ("Megalopolis", 22.15, 37.41), ("Messene", 21.92, 37.18), ("Olympia", 21.63, 37.64),
    ("Elis", 21.34, 37.68), ("Patrae", 21.73, 38.25), ("Sicyon", 22.71, 37.98),
    ("Epidaurus", 23.15, 37.63), ("Nauplia", 22.80, 37.57), ("Midea", 22.85, 37.63),
    ("Megara", 23.34, 37.99), ("Eleusis", 23.54, 38.04), ("Marathon", 23.98, 38.15),
    ("Sunium", 23.98, 37.65), ("Aegina", 23.43, 37.75), ("Thebae_Boeotiae", 23.32, 38.32),
    ("Plataeae", 23.27, 38.22), ("Orchomenus", 22.97, 38.49), ("Chaeronea", 22.85, 38.50),
    ("Delphi", 22.50, 38.48), ("Naupactus", 21.83, 38.39), ("Larissa", 22.42, 39.64),
    ("Pharsalus", 22.38, 39.30), ("Demetrias", 22.98, 39.35), ("Pydna", 22.53, 40.40),
    ("Pella", 22.52, 40.76), ("Beroea", 22.20, 40.52), ("Dium", 22.50, 40.19),
    ("Cassandrea", 23.43, 40.25), ("Amphipolis", 23.85, 40.82), ("Philippi", 24.28, 41.01),
    ("Neapolis_Macedoniae", 24.42, 40.94), ("Abdera", 24.98, 40.94), ("Perinthus", 27.95, 40.97),
    # Anatolia
    ("Nicaea", 29.72, 40.43), ("Nicomedia", 29.92, 40.77), ("Prusa", 29.06, 40.18),
    ("Cyzicus", 27.88, 40.38), ("Lampsacus", 26.68, 40.35), ("Ilium", 26.24, 39.96),
    ("Alexandria_Troas", 26.24, 39.75), ("Assus", 26.34, 39.49), ("Adramyttium", 26.94, 39.58),
    ("Mytilene", 26.55, 39.11), ("Elaea", 26.97, 39.05), ("Clazomenae", 27.00, 38.35),
    ("Erythrae", 26.47, 38.32), ("Teos", 26.78, 38.18), ("Priene", 27.30, 37.66),
    ("Miletus", 27.28, 37.53), ("Magnesia", 27.44, 37.85), ("Tralles", 27.84, 37.86),
    ("Nysa", 28.14, 37.90), ("Aphrodisias", 28.71, 37.71), ("Laodicea_Phrygiae", 29.11, 37.84),
    ("Hierapolis", 29.13, 37.93), ("Apamea", 30.16, 38.07), ("Aezani", 29.35, 39.60),
    ("Cotyaeum", 29.98, 39.45), ("Dorylaeum", 30.52, 39.78), ("Pessinus", 31.55, 39.34),
    ("Ancyra", 32.86, 39.94), ("Gordium", 31.98, 39.66),
    # Egypt
    ("Arsinoe", 30.83, 29.35), ("Oxyrhynchus", 30.65, 28.53), ("Antinoopolis", 30.88, 27.81),
    ("Hermopolis", 30.80, 27.78), ("Lycopolis", 31.32, 27.20), ("Panopolis", 31.74, 26.56),
    ("Tentyra", 32.71, 26.14), ("Apollonopolis", 33.07, 24.98), ("Syene", 32.90, 24.09),
    ("Babylon_Aegypti", 31.23, 30.02), ("Heliopolis", 31.30, 30.13), ("Bubastis", 31.68, 30.57),
    ("Tanis", 31.88, 30.97), ("Sais", 30.79, 30.97), ("Naucratis", 30.36, 30.90),
    ("Thmuis", 31.50, 30.72), ("Sebennytus", 31.25, 30.85),
]

KINDS = (("p_town_", TOWNS), ("p_castle_", CASTLES), ("p_village_", VILLAGES))


# ------------------------------------------------------------- the real map mesh
class MapFaces(object):
    """Faces of the built map.txt, bucketed in a grid.

    The analytic sampler can disagree with the mesh a few tenths of a unit from
    the shore (a face straddling the coastline keeps its averaged height), and a
    settlement on such a face is drawn standing in the sea.  Testing against the
    real faces is what the game actually sees.
    """

    def __init__(self, path="map.txt", cell=4.0):
        raw = io.open(path, encoding="latin-1", newline="").read()
        lines = raw.replace(chr(13) + chr(10), chr(10)).split(chr(10))
        n = int(lines[0])
        self.V = [tuple(float(c) for c in l.split()) for l in lines[1:1 + n]]
        m = int(lines[1 + n])
        self.F = []
        for line in lines[2 + n:2 + n + m]:
            tk = line.split()
            self.F.append((int(tk[0]), int(tk[3]), int(tk[4]), int(tk[5])))
        self.cell = cell
        self.buckets = {}
        for fi, (_code, a, b, c) in enumerate(self.F):
            xs = (self.V[a][0], self.V[b][0], self.V[c][0])
            ys = (self.V[a][1], self.V[b][1], self.V[c][1])
            for i in range(int(math.floor(min(xs) / cell)), int(math.floor(max(xs) / cell)) + 1):
                for j in range(int(math.floor(min(ys) / cell)), int(math.floor(max(ys) / cell)) + 1):
                    self.buckets.setdefault((i, j), []).append(fi)

    def face(self, x, y):
        """(terrain code, mean height) of the face containing (x, y)"""
        key = (int(math.floor(x / self.cell)), int(math.floor(y / self.cell)))
        for fi in self.buckets.get(key, ()):
            code, a, b, c = self.F[fi]
            ax, ay = self.V[a][0], self.V[a][1]
            bx, by = self.V[b][0], self.V[b][1]
            cx, cy = self.V[c][0], self.V[c][1]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            l1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
            l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
            if l1 >= 0.0 and l2 >= 0.0 and l1 + l2 <= 1.0:
                return code, (self.V[a][2] + self.V[b][2] + self.V[c][2]) / 3.0
        return None, None


WATER_CODES = (0, 7, 8)


def place(x, y, grid, planned, min_gap=2.0):
    """Nearest mesh land point, kept as close as possible to the historical spot."""
    for step in range(0, 26):
        r = step * 0.45
        n = 1 if step == 0 else 45
        best = None
        for a in range(n):
            px = x + r * math.cos(a * 2.0 * math.pi / n)
            py = y + r * math.sin(a * 2.0 * math.pi / n)
            code, z = grid.face(px, py)
            if code is None or code in WATER_CODES or z < 0.45:
                continue
            if any((px - qx) ** 2 + (py - qy) ** 2 < min_gap * min_gap
                   for _slot, qx, qy in planned):
                continue
            d = (px - x) ** 2 + (py - y) ** 2
            if best is None or d < best[0]:
                best = (d, px, py)
        if best is not None:
            return best[1], best[2]
    return x, y


def apply(grid=None):
    if grid is None:
        grid = MapFaces()
    path = "parties.txt"
    raw = io.open(path, encoding="latin-1", newline="").read()
    crlf = "\r\n" in raw
    lines = raw.replace("\r\n", "\n").split("\n")
    planned = []          # (line index, x, y) for spacing checks
    done = {"town": 0, "castle": 0, "village": 0}
    missing = []
    for i, line in enumerate(lines):
        tk = line.split()
        if len(tk) < 20:
            continue
        for prefix, table in KINDS:
            if not tk[3].startswith(prefix):
                continue
            idx = int(tk[3][len(prefix):]) - 1
            if idx >= len(table):
                missing.append(tk[3])
                continue
            name, lon, lat = table[idx]
            x, y = place(*W.P(lon, lat), grid=grid, planned=planned)
            tk[4] = name
            for n in range(3):
                tk[14 + 2 * n] = "%.6f" % x
                tk[15 + 2 * n] = "%.6f" % y
            lead = line[:len(line) - len(line.lstrip())]
            trail = line[len(line.rstrip()):]
            lines[i] = lead + " ".join(tk) + trail
            planned.append((tk[3], x, y))
            done[prefix[2:-1]] += 1
    out = "\n".join(lines)
    if crlf:
        out = out.replace("\n", "\r\n")
    io.open(path, "w", encoding="latin-1", newline="").write(out)
    return done, missing, len(planned)


if __name__ == "__main__":
    done, missing, total = apply()
    print("settlements placed:", done, "total", total)
    if missing:
        print("no historical entry for:", len(missing), "slots ->", missing[:8])
