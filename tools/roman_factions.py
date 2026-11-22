# -*- coding: utf-8 -*-
"""Political layer of the Roman world: the real powers of the age.

The 21 kingdom slots of factions.txt are renamed to the states that actually
shared the Mediterranean in the age of the Roman Republic (the generation of
the Second Punic War, c. 218 BC):

    Rome and its allies, Carthage, Syracuse, Numidia, the Celtiberian and
    Gallic tribes, Massilia, the Britons, Antigonid Macedonia, the Achaean and
    Aetolian leagues, Sparta, Athens, Attalid Pergamon, Bithynia, Galatia,
    Cappadocia, the Seleucid empire, Ptolemaic Egypt, Nabataea and Parthia.

Every settlement (town/castle/village) is given to the power holding the
closest of its historical cities; the same faction is written into parties.txt
and into the 119 party_set_faction statements of game_start in scripts.txt, so
nothing is left neutral and the runtime cannot override the map.

Usage:
    python tools/roman_factions.py            # dry run, report only
    python tools/roman_factions.py --write    # apply changes
"""

import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import historic as hist  # noqa: E402

PARTY_BASE = 648518346341351424
FACTION_BASE = 432345564227567616
PARTY_SET_FACTION_OP = "936748722493063390"
FIRST_KINGDOM_INDEX = 16          # fac_kingdom_1 in factions.txt
NEUTRAL_FACTION = 3

# a degree of longitude is ~0.8 of a degree of latitude at 37N
LON_SCALE = 0.8

# (token shown on the map, colour, [historical cities that define its land])
POWERS = [
    ("Res_Publica_Romana", 12597547, [
        (12.50, 41.90), (12.29, 41.75), (14.25, 41.08), (14.25, 40.85),
        (17.94, 40.64), (17.24, 40.47), (17.13, 39.08), (15.65, 38.11),
        (16.26, 38.24), (16.10, 38.68), (16.25, 39.30), (16.55, 39.72),
        (16.82, 40.38), (16.68, 40.22), (15.90, 40.28), (15.82, 40.96),
        (16.06, 41.22), (15.33, 41.51), (15.70, 41.50), (15.90, 41.60),
        (15.05, 40.98), (14.78, 41.13), (14.99, 40.42), (15.16, 40.16),
        (14.67, 40.75), (14.77, 40.68), (14.53, 40.93), (14.05, 40.85),
        (14.12, 40.83), (13.77, 41.24), (13.61, 41.26), (13.24, 41.29),
        (13.53, 42.10), (13.83, 42.12), (13.70, 41.49), (13.83, 41.49),
        (14.05, 41.48), (14.23, 41.60), (14.60, 41.43), (14.06, 41.25),
        (12.39, 43.11), (11.88, 43.46), (11.25, 43.77), (10.40, 43.72),
        (12.57, 44.06), (13.51, 43.62), (12.28, 44.42), (12.63, 41.45),
        (13.36, 38.12), (12.43, 37.80), (12.50, 38.02), (12.84, 37.94),
        (12.59, 38.04), (13.53, 38.09), (13.72, 37.98), (14.03, 37.99),
        (12.60, 37.58), (13.10, 37.39), (9.11, 39.22), (9.50, 40.92),
        (8.44, 39.87), (8.40, 40.85), (9.51, 42.11), (14.51, 35.90),
    ]),
    ("Carthaginian_Empire", 8207512, [
        (10.32, 36.85), (10.05, 37.06), (10.64, 35.83), (10.90, 35.60),
        (10.71, 35.30), (10.10, 33.88), (14.29, 32.64), (13.18, 32.90),
        (12.49, 32.79), (-6.29, 36.53), (-0.98, 37.60), (-4.42, 36.72),
        (-4.78, 37.88), (-5.98, 37.38), (2.90, 39.60),
    ]),
    ("Kingdom_of_Syracuse", 15105570, [
        (15.29, 37.07), (15.09, 37.50), (14.99, 37.31), (15.29, 37.85),
        (15.18, 37.20), (14.44, 36.87), (14.25, 37.07), (14.93, 36.94),
        (15.05, 38.15),
    ]),
    ("Kingdom_of_Numidia", 8359053, [
        (7.77, 36.90), (6.61, 36.36), (6.50, 35.50),
    ]),
    ("Hispania_Celtibera", 13938685, [
        (1.25, 41.12), (-0.88, 41.65), (3.10, 42.13), (-2.44, 41.81),
        (-4.02, 39.86), (-9.13, 38.72), (-5.66, 40.96), (-0.27, 39.68),
        (-0.48, 38.36), (-6.50, 42.00), (-8.00, 42.80),
    ]),
    ("Arverni_Gaul", 2596448, [
        (4.03, 46.92), (4.83, 45.76), (-0.58, 44.84), (1.44, 43.60),
        (4.87, 45.52), (4.81, 43.95), (4.36, 43.84), (2.35, 48.85),
        (9.19, 45.46), (10.99, 45.44), (10.22, 45.54), (11.88, 45.41),
        (10.02, 45.13), (10.93, 44.65), (11.34, 44.49), (10.33, 44.80),
        (9.69, 45.05), (9.16, 45.19), (7.69, 45.07), (8.03, 44.70),
        (8.93, 44.41), (13.37, 45.77),
    ]),
    ("Massilia", 2729913, [
        (5.37, 43.30), (7.13, 43.58), (6.64, 43.43), (3.47, 43.31),
        (7.27, 43.72),
    ]),
    ("Britannia", 1486981, [
        (-0.13, 51.51), (0.90, 51.89), (-1.08, 53.96), (-1.34, 51.35),
        (-1.32, 51.06), (-3.00, 52.00), (-2.00, 54.50),
    ]),
    ("Antigonid_Macedonia", 10502144, [
        (22.52, 40.76), (22.94, 40.64), (22.53, 40.40), (22.20, 40.52),
        (22.50, 40.19), (22.98, 39.35), (22.42, 39.64), (22.38, 39.30),
        (23.43, 40.25), (23.85, 40.82), (24.28, 41.01), (24.42, 40.94),
        (28.98, 41.01),
    ]),
    ("Achaean_League", 1749148, [
        (22.93, 37.94), (22.71, 37.98), (21.73, 38.25), (22.15, 37.41),
        (22.73, 37.63), (22.08, 38.25), (22.80, 37.57), (23.34, 37.99),
        (23.15, 37.63), (21.92, 37.18),
    ]),
    ("Kingdom_of_Sparta", 11549230, [
        (22.43, 37.08), (22.42, 37.45),
    ]),
    ("Aetolian_League", 8218120, [
        (21.66, 38.51), (21.83, 38.39), (22.50, 38.48), (21.63, 37.64),
        (21.34, 37.68),
    ]),
    ("Athens", 2647206, [
        (23.73, 37.98), (23.54, 38.04), (23.98, 38.15), (23.98, 37.65),
        (23.43, 37.75),
    ]),
    ("Attalid_Pergamon", 11499973, [
        (27.18, 39.12), (26.97, 39.05), (26.94, 39.58), (26.34, 39.49),
        (26.24, 39.75), (26.24, 39.96), (26.68, 40.35), (27.88, 40.38),
        (26.55, 39.11),
    ]),
    ("Kingdom_of_Bithynia", 15495267, [
        (29.92, 40.77), (29.72, 40.43), (29.06, 40.18),
    ]),
    ("Galatia", 12154638, [
        (32.86, 39.94), (31.55, 39.34), (31.98, 39.66),
    ]),
    ("Thracian_Kingdom", 11088422, [
        (25.60, 42.40), (26.30, 42.10), (26.30, 41.70), (27.95, 40.97),
        (24.98, 40.94),
    ]),
    ("Seleucid_Empire", 3049153, [
        (36.16, 36.20), (35.93, 36.12), (35.78, 35.52), (35.86, 34.86),
        (35.84, 34.44), (35.50, 33.89), (36.29, 33.51), (36.75, 36.74),
        (37.87, 37.06), (34.90, 36.92), (35.32, 37.00), (35.63, 36.96),
        (35.90, 37.24), (36.40, 35.40), (36.72, 34.73), (38.27, 34.55),
    ]),
    ("Ptolemaic_Egypt", 14060816, [
        (29.92, 31.20), (31.25, 29.85), (32.60, 31.05), (21.86, 32.82),
        (20.95, 32.70), (20.07, 32.12), (25.15, 31.35), (32.65, 25.70),
        (32.82, 26.00), (34.24, 26.15), (30.83, 29.35), (31.23, 30.02),
        (35.20, 33.27), (35.37, 33.56), (35.07, 32.92), (34.45, 31.50),
        (34.55, 31.67), (34.75, 31.93), (34.92, 32.62), (34.89, 32.50),
        (32.42, 34.75),
    ]),
    ("Nabataean_Kingdom", 13266718, [
        (35.44, 30.33), (36.48, 32.52),
    ]),
    ("Parthian_Empire", 7091331, [
        (41.20, 37.07), (39.03, 36.86), (38.79, 37.15), (40.73, 34.75),
    ]),
]

# settlements whose nearest city would put them in the wrong state
OVERRIDES = {
    "Aquileia": "Res_Publica_Romana",
    "Tegea": "Kingdom_of_Sparta",
    "Megara": "Achaean_League",
    "Delphi": "Aetolian_League",
    "Palmyra": "Seleucid_Empire",
    "Tacape": "Carthaginian_Empire",
    "Melita": "Res_Publica_Romana",
    "Aleria": "Res_Publica_Romana",
    "Genua": "Arverni_Gaul",
    "Emporiae": "Hispania_Celtibera",
    "Saguntum": "Hispania_Celtibera",
    "Byzantium": "Antigonid_Macedonia",
    "Perinthus": "Thracian_Kingdom",
    "Abdera": "Thracian_Kingdom",
    "Zeugma": "Seleucid_Empire",
    "Dura_Europos": "Parthian_Empire",
    "Bostra": "Nabataean_Kingdom",
    "Petra": "Nabataean_Kingdom",
}

SETTLEMENT_PREFIXES = ("p_town", "p_castle", "p_village")


def power_of(name, lon, lat):
    if name in OVERRIDES:
        return OVERRIDES[name]
    best, best_d = None, None
    for token, _color, anchors in POWERS:
        for alon, alat in anchors:
            d = ((lon - alon) * LON_SCALE) ** 2 + (lat - alat) ** 2
            if best_d is None or d < best_d:
                best, best_d = token, d
    return best


def settlement_coords():
    coords = {}
    for group in (hist.TOWNS, hist.CASTLES, hist.VILLAGES):
        for name, lon, lat in group:
            coords[name] = (lon, lat)
    return coords


def read_lines(path):
    with io.open(path, "rb") as fh:
        return fh.read().decode("utf-8", "replace").split("\n")


def write_lines(path, lines):
    with io.open(path, "wb") as fh:
        fh.write("\r\n".join(l.rstrip("\r") for l in lines).encode("utf-8"))


def settlement_parties(lines):
    out = []
    for raw in lines[2:]:
        tok = raw.split()
        if len(tok) > 8 and tok[3].startswith(SETTLEMENT_PREFIXES):
            out.append({"index": int(tok[1]), "id": tok[3], "name": tok[4],
                        "raw": raw})
    return out


def plan():
    coords = settlement_coords()
    lines = read_lines(os.path.join(ROOT, "parties.txt"))
    parties = settlement_parties(lines)
    order = [t for t, _c, _a in POWERS]
    assign = {}
    unknown = []
    for p in parties:
        if p["name"] not in coords:
            unknown.append(p["name"])
            power = order[0]
        else:
            lon, lat = coords[p["name"]]
            power = power_of(p["name"], lon, lat)
        p["power"] = power
        assign[p["index"]] = FIRST_KINGDOM_INDEX + order.index(power)
    return parties, assign, unknown


def rewrite_parties(parties, assign):
    path = os.path.join(ROOT, "parties.txt")
    lines = read_lines(path)
    done = 0
    for i, raw in enumerate(lines):
        tok = raw.split()
        if len(tok) > 8 and tok[3].startswith(SETTLEMENT_PREFIXES):
            idx = int(tok[1])
            if idx in assign:
                parts = raw.split(" ")
                seen = 0
                for j, piece in enumerate(parts):
                    if piece:
                        if seen == 8:
                            parts[j] = str(assign[idx])
                            done += 1
                            break
                        seen += 1
                lines[i] = " ".join(parts)
    write_lines(path, lines)
    return done


def rewrite_scripts(assign):
    path = os.path.join(ROOT, "scripts.txt")
    lines = read_lines(path)
    changed = 0
    for i, raw in enumerate(lines):
        if PARTY_SET_FACTION_OP not in raw:
            continue
        tok = raw.split()
        touched = False
        for j in range(len(tok) - 2):
            if (tok[j] == PARTY_SET_FACTION_OP
                    and tok[j + 1].isdigit() and tok[j + 2].isdigit()):
                pidx = int(tok[j + 1]) - PARTY_BASE
                if pidx in assign:
                    tok[j + 2] = str(FACTION_BASE + assign[pidx])
                    changed += 1
                    touched = True
        if touched:
            lines[i] = " " + " ".join(tok)
    write_lines(path, lines)
    return changed


def rewrite_factions():
    path = os.path.join(ROOT, "factions.txt")
    lines = read_lines(path)
    for i, raw in enumerate(lines):
        tok = raw.split()
        if len(tok) > 4 and tok[1].startswith("fac_kingdom_"):
            num = int(tok[1].rsplit("_", 1)[1])
            if 1 <= num <= len(POWERS):
                tok[2] = POWERS[num - 1][0]
                tok[4] = str(POWERS[num - 1][1])
                lines[i] = " " + " ".join(tok) + " "
    write_lines(path, lines)


def main():
    write = "--write" in sys.argv
    parties, assign, unknown = plan()
    if unknown:
        print("!! settlements without coordinates:", unknown)
    counts = {}
    for p in parties:
        counts[p["power"]] = counts.get(p["power"], 0) + 1
    print("powers: %d, settlements: %d" % (len(POWERS), len(parties)))
    for token, _c, _a in POWERS:
        print("  %-22s %3d  -> faction id %d" % (
            token, counts.get(token, 0),
            FIRST_KINGDOM_INDEX + [t for t, _c2, _a2 in POWERS].index(token)))
    empty = [t for t, _c, _a in POWERS if not counts.get(t)]
    if empty:
        print("!! empty powers:", empty)
    if not write:
        print("dry run (pass --write to apply)")
        return
    rewrite_factions()
    n_parties = rewrite_parties(parties, assign)
    n_scripts = rewrite_scripts(assign)
    print("parties.txt updated: %d" % n_parties)
    print("scripts.txt assignments updated: %d" % n_scripts)


if __name__ == "__main__":
    main()
