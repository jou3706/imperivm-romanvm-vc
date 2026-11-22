# -*- coding: utf-8 -*-
"""Overlay the political layer on the rendered map.

Runs render_map.py first (so the base picture is current), then stamps every
settlement with the colour of the faction that owns it in parties.txt.
Squares are bigger for towns and castles, small for villages.
"""
import io
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    i = 8
    w = h = None
    idat = b""
    while i < len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        body = data[i + 8:i + 8 + ln]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif tag == b"IDAT":
            idat += body
        i += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    px = bytearray(w * h * 3)
    for y in range(h):
        row = raw[y * stride:(y + 1) * stride]
        px[y * w * 3:(y + 1) * w * 3] = row[1:]
    return w, h, px


def write_png(path, w, h, px):
    rows = b"".join(b"\x00" + bytes(px[r * w * 3:(r + 1) * w * 3]) for r in range(h))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))
    open(path, "wb").write(png)


def load_faction_colours():
    colours = {}
    for line in io.open(os.path.join(ROOT, "factions.txt"), encoding="latin-1"):
        tok = line.split()
        if len(tok) > 4 and tok[1].startswith("fac_kingdom_"):
            c = int(tok[4])
            colours[len(colours) + 16] = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
    return colours


def main():
    subprocess.check_call([sys.executable, os.path.join(HERE, "render_map.py")])
    w, h, px = read_png(os.path.join(HERE, "map_from_file.png"))
    X0, X1, YTOP, YBOT = -345.0, 285.0, 245.0, -240.0

    def to_px(x, y):
        return (x - X0) * w / (X1 - X0), (YTOP - y) * h / (YTOP - YBOT)

    colours = load_faction_colours()
    lines = io.open(os.path.join(ROOT, "parties.txt"), encoding="latin-1").read().replace("\r\n", "\n").split("\n")
    for line in lines:
        tok = line.split()
        if len(tok) < 20 or not tok[3].startswith(("p_town_", "p_castle_", "p_village_")):
            continue
        try:
            fac = int(tok[8])
            x, y = float(tok[14]), float(tok[15])
        except ValueError:
            continue
        col = colours.get(fac, (255, 0, 255))
        i, j = to_px(x, y)
        r = 4 if tok[3].startswith("p_town_") else (3 if tok[3].startswith("p_castle_") else 1)
        for dj in range(-r - 1, r + 2):
            for di in range(-r - 1, r + 2):
                xx, yy = int(i) + di, int(j) + dj
                if not (0 <= xx < w and 0 <= yy < h):
                    continue
                o = (yy * w + xx) * 3
                edge = max(abs(di), abs(dj)) > r
                if edge:
                    if r > 1:
                        px[o:o + 3] = bytes((20, 20, 20))
                else:
                    px[o:o + 3] = bytes(col)
    out = os.path.join(HERE, "map_political.png")
    write_png(out, w, h, px)
    print(out, "settlements coloured")


if __name__ == "__main__":
    main()
