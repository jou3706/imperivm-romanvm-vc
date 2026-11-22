# -*- coding: utf-8 -*-
"""Spread the settlements of parties.txt so every icon and label is visible.

Real Roman cities sit 15-30 km apart, which on this map is 1-3 map units -- and
a town icon is about 8 units wide.  That is why Roma disappeared under Veii,
Tusculum, Ostia and Tibur.  This tool relaxes the settlements with a minimum
distance per pair of settlement types:

    * a town never moves (they are the capitals / map anchors) -- above all
      Roma itself stays exactly on its historical coordinates;
    * castles move a little, villages move the most;
    * every new position is checked against the real map faces (walkable land,
      never water, never a river or bridge face) and never leaves the map.

Usage:
    python tools/declutter.py            # dry run, report only
    python tools/declutter.py --write    # apply changes
"""
import io
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import coastline  # noqa: E402

ROOT = os.path.dirname(HERE)
PARTY_PREFIXES = ("p_town", "p_castle", "p_village")

# minimum distance in map units (1 unit ~ 7 km) between two settlement kinds
MIN = {
    ("town", "town"): 9.0,
    ("castle", "town"): 6.2,
    ("town", "village"): 5.6,
    ("castle", "castle"): 5.2,
    ("castle", "village"): 4.3,
    ("village", "village"): 3.8,
}

PRIORITY = {"town": 3, "castle": 2, "village": 1}

# how far a settlement of each kind may leave its historical coordinates
CAP = {"town": 2.5, "castle": 4.0, "village": 7.0}

# never touched: the great cities stay on their historical coordinates
FIXED = {"Roma"}

STEP = 0.6          # max move per relaxation pass
PASSES = 500
LAND_MIN = 0.7      # keep this far from the sea (so the icon is not in water)


def read_lines(path):
    with io.open(path, "rb") as fh:
        return fh.read().decode("latin-1").split("\n")


def write_lines(path, lines):
    with io.open(path, "wb") as fh:
        fh.write("\r\n".join(l.rstrip("\r") for l in lines).encode("latin-1"))


def load_sites(lines):
    sites = []
    for i, raw in enumerate(lines):
        tok = raw.split()
        if len(tok) > 19 and tok[3].startswith(PARTY_PREFIXES):
            kind = tok[3].split("_")[1]
            sites.append({"line": i, "name": tok[4], "kind": kind,
                          "x": float(tok[14]), "y": float(tok[15])})
    return sites


def min_matrix(kinds):
    n = len(kinds)
    m = np.zeros((n, n))
    for i, a in enumerate(kinds):
        for j, b in enumerate(kinds):
            m[i, j] = MIN[tuple(sorted((a, b)))]
    np.fill_diagonal(m, 0.0)
    return m


def land_ok(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    land = np.asarray(coastline.is_land(x, y)) >= 0.5
    return land & (np.asarray(coastline.land_sd(x, y)) > LAND_MIN)


def relax(pos, prio, fixed, mins, caps):
    n = len(pos)
    home = pos.copy()
    for _ in range(PASSES):
        d = pos[:, None, :] - pos[None, :, :]
        dist = np.hypot(d[..., 0], d[..., 1])
        overlap = np.where(dist > 1e-6, np.maximum(mins - dist, 0.0), 0.0)
        np.fill_diagonal(overlap, 0.0)
        if overlap.max() < 1e-3:
            break
        # the weaker settlement gives way: villages move, towns stay put
        share = np.where(prio[:, None] < prio[None, :], 1.0,
                         np.where(prio[:, None] > prio[None, :], 0.0, 0.5))
        share = np.where(fixed[:, None], 0.0,
                         np.where(fixed[None, :], 1.0, share))
        unit = d / np.where(dist > 1e-6, dist, 1.0)[..., None]
        push = np.einsum("ij,ij,ijk->ik", overlap * share, np.ones_like(dist), unit)
        mag = np.hypot(push[:, 0], push[:, 1])
        scale = np.where(mag > STEP, STEP / np.maximum(mag, 1e-9), 1.0)
        push *= scale[:, None]
        moved = mag > 1e-6
        if not moved.any():
            break
        cand = pos + push
        vec = cand - home
        far = np.hypot(vec[:, 0], vec[:, 1])
        over = far > caps
        if over.any():
            cand[over] = home[over] + vec[over] * (caps[over] / far[over])[:, None]
        ok = land_ok(cand[:, 0], cand[:, 1])
        # points that would land in the sea: try shorter moves and side steps
        bad = moved & ~ok
        if bad.any():
            for frac, ang in ((1.0, 30), (1.0, -30), (0.8, 0), (1.0, 55), (1.0, -55),
                              (0.6, 0), (1.0, 80), (1.0, -80)):
                todo = np.where(bad)[0]
                if not len(todo):
                    break
                step = push[todo] * frac
                if ang:
                    a = math.radians(ang)
                    ca, sa = math.cos(a), math.sin(a)
                    step = np.column_stack([step[:, 0] * ca - step[:, 1] * sa,
                                            step[:, 0] * sa + step[:, 1] * ca])
                trial = pos[todo] + step
                good = land_ok(trial[:, 0], trial[:, 1])
                if good.any():
                    idx = todo[good]
                    pos[idx] = trial[good]
                    cand[idx] = trial[good]
                bad[todo[good]] = False
        take = moved & land_ok(cand[:, 0], cand[:, 1])
        pos[take] = cand[take]
    dist = np.hypot(*(pos[:, None, :] - pos[None, :, :]).transpose(2, 0, 1))
    # settle on land for anything that started (or ended) badly placed
    for i in range(n):
        if land_ok(pos[i, 0], pos[i, 1]):
            continue
        best = None
        for r in np.arange(0.5, float(caps[i]) + 0.01, 0.5):
            for a in range(0, 360, 15):
                rad = math.radians(a)
                tx = home[i, 0] + r * math.cos(rad)
                ty = home[i, 1] + r * math.sin(rad)
                if land_ok(tx, ty):
                    best = (tx, ty)
                    break
            if best:
                break
        if best:
            pos[i] = best
    clash = np.where((dist < mins - 0.05) & (dist > 1e-6), 1, 0)
    pairs = int(clash.sum() // 2)
    return pos, pairs


def main():
    path = os.path.join(ROOT, "parties.txt")
    lines = read_lines(path)
    sites = load_sites(lines)
    pos = np.array([[s["x"], s["y"]] for s in sites], dtype=np.float64)
    home = pos.copy()
    prio = np.array([PRIORITY[s["kind"]] for s in sites], dtype=np.float64)
    fixed = np.array([s["name"] in FIXED for s in sites])
    caps = np.array([CAP[s["kind"]] for s in sites], dtype=np.float64)
    kinds = [s["kind"] for s in sites]
    mins = min_matrix(kinds)
    print("settlements: %d (fixed: %s)" % (len(sites), sorted(FIXED)))
    before = np.hypot(*(pos[:, None, :] - pos[None, :, :]).transpose(2, 0, 1))
    close_before = int((np.where((before < mins) & (before > 1e-6), 1, 0).sum()) // 2)
    print("overlapping pairs before: %d" % close_before)
    pos, left = relax(pos, prio, fixed, mins, caps)
    delta = np.hypot(pos[:, 0] - home[:, 0], pos[:, 1] - home[:, 1])
    if not land_ok(pos[:, 0], pos[:, 1]).all():
        print("!! settlements off walkable land:",
              [sites[i]["name"] for i in np.where(~land_ok(pos[:, 0], pos[:, 1]))[0]])
    print("overlapping pairs after : %d" % left)
    print("moved %.0f of %d settlements, median %.2f units, max %.2f (~%.0f km)"
          % (int((delta > 0.05).sum()), len(sites), float(np.median(delta)),
             float(delta.max()), float(delta.max()) * 7.0))
    worst = np.argsort(-delta)[:8]
    for i in worst:
        print("   %-22s %-7s %5.2f units" % (sites[i]["name"], sites[i]["kind"], delta[i]))
    if "--write" not in sys.argv:
        print("dry run (pass --write to apply)")
        return
    for i, s in enumerate(sites):
        parts = lines[s["line"]].split(" ")
        seen = 0
        for j, piece in enumerate(parts):
            if piece:
                if seen in (14, 16, 18):
                    parts[j] = "%.6f" % pos[i, 0]
                elif seen in (15, 17, 19):
                    parts[j] = "%.6f" % pos[i, 1]
                seen += 1
        lines[s["line"]] = " ".join(parts)
    write_lines(path, lines)
    print("parties.txt updated")


if __name__ == "__main__":
    main()
