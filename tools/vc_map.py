"""Put the Roman world into the Viking Conquest copy.

* map.txt : same mesh as VC (±282 grid = our world scale), new heights and
            terrain codes from roman_mapgen.
* parties.txt : VC's settlements/land parties keep their coordinates but are
            pushed off water/river/impassable faces (ships left alone).
"""
import io, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROMAN = os.path.abspath(os.path.join(HERE, "..", "..", "Native Tactical", "tools"))
sys.path.insert(0, ROMAN)
import roman_mapgen as M  # noqa: E402


def load(name):
    return io.open(name, encoding="latin-1", newline="").read().replace("\r\n", "\n")


def save(name, text):
    io.open(name, "w", encoding="latin-1", newline="").write(text)


def build_map():
    lines = load("map.txt").split("\n")
    n = int(lines[0])
    verts = [l.split() for l in lines[1:1 + n]]
    zs = []
    for v in verts:
        x, y = float(v[0]), float(v[1])
        z = M.height(x, y)
        zs.append(z)
        v[2] = "%.6f" % z
    for i in range(n):
        lines[1 + i] = " ".join(verts[i])
    nf = int(lines[1 + n])
    land = 0
    for i in range(nf):
        f = lines[2 + n + i].split()
        a, b, c = int(f[3]), int(f[4]), int(f[5])
        x = (float(verts[a][0]) + float(verts[b][0]) + float(verts[c][0])) / 3.0
        y = (float(verts[a][1]) + float(verts[b][1]) + float(verts[c][1])) / 3.0
        z = (zs[a] + zs[b] + zs[c]) / 3.0
        code = M.terrain(x, y, z)
        f[0] = str(code)
        lines[2 + n + i] = " ".join(f)
        if code in (2, 3, 4, 5, 10, 11, 12, 13):
            land += 1
    save("map.txt", "\n".join(lines))
    return n, nf, land


def on_land(x, y):
    return M.height(x, y) > 0.05 and M.land_sd(x, y) > 0.25


def snap_parties():
    lines = load("parties.txt").split("\n")
    moved = kept = ships = 0
    for i, line in enumerate(lines):
        tk = line.split()
        if len(tk) < 20 or not tk[3].startswith("p_"):
            continue
        flags = int(tk[5])
        x, y = float(tk[14]), float(tk[15])
        if on_land(x, y):
            kept += 1
            continue
        if flags & 0x200:  # pf_is_ship – must stay at sea
            ships += 1
            continue
        spot = None
        for r in range(1, 60):
            for a in range(24):
                px = x + r * 1.2 * math.cos(a * math.pi / 12)
                py = y + r * 1.2 * math.sin(a * math.pi / 12)
                if on_land(px, py):
                    spot = (px, py)
                    break
            if spot:
                break
        if not spot:
            continue
        for n in range(3):
            tk[14 + 2 * n] = "%.6f" % spot[0]
            tk[15 + 2 * n] = "%.6f" % spot[1]
        lines[i] = " " + " ".join(tk) + " "
        moved += 1
    save("parties.txt", "\n".join(lines))
    return moved, kept, ships


if __name__ == "__main__":
    n, nf, land = build_map()
    print("map.txt: verts %d faces %d land %d (%.0f%%)" % (n, nf, land, 100.0 * land / nf))
    moved, kept, ships = snap_parties()
    print("parties: moved %d, already on land %d, ships kept at sea %d" % (moved, kept, ships))
