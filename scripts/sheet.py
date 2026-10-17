"""Labeled contact sheet of PNG frames (alpha composited over a backdrop color). For review checkpoints.
Usage: .venv/bin/python scripts/sheet.py <out.jpg> <cols> <backdrop hex> <label=path> [...]
"""
import sys

from PIL import Image, ImageDraw, ImageFont

out, cols, bg = sys.argv[1], int(sys.argv[2]), sys.argv[3]
items = [a.split("=", 1) for a in sys.argv[4:]]
tiles = []
for label, path in items:
    im = Image.open(path).convert("RGBA")
    base = Image.new("RGBA", im.size, bg)
    tiles.append((label, Image.alpha_composite(base, im).convert("RGB")))
w, h = tiles[0][1].size
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h), "black")
font = ImageFont.truetype("assets/fonts/JetBrainsMono[wght].ttf", max(12, h // 22))
d = ImageDraw.Draw(sheet)
for i, (label, im) in enumerate(tiles):
    x, y = (i % cols) * w, (i // cols) * h
    sheet.paste(im, (x, y))
    d.text((x + 6, y + 4), label, fill="yellow", font=font)
sheet.save(out, quality=88)
