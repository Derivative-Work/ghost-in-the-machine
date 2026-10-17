"""C1 review sheet: two reference stills per inspiration video (top) beside the averaged-style test frame (bottom).

Usage: .venv/bin/python scripts/c1_sheet.py <test_frame.png> <out.jpg>
"""
import sys

from PIL import Image, ImageDraw, ImageFont

# Hand-picked from each contact_every5s.jpg: one type-led frame and one scene-led frame per video.
PICKS = [
    ("accept-all", "0010"), ("accept-all", "0029"),
    ("end-of-the-show", "0002"), ("end-of-the-show", "0029"),
    ("lgtm", "0018"), ("lgtm", "0034"),
    ("not-my-fault", "0009"), ("not-my-fault", "0032"),
    ("run-it-again", "0010"), ("run-it-again", "0029"),
]
W, H, COLS, PAD, LABEL = 384, 216, 5, 8, 28
MONO = "assets/fonts/JetBrainsMono[wght].ttf"


def main():
    test_path, out = sys.argv[1:3]
    font = ImageFont.truetype(MONO, 18)
    rows = (len(PICKS) + COLS - 1) // COLS
    ref_h = rows * (H + LABEL) + PAD
    test_w = COLS * W + (COLS - 1) * PAD
    test_h = test_w * 9 // 16
    sheet = Image.new("RGB", (test_w + 2 * PAD, ref_h + LABEL + test_h + 2 * PAD), "#09080b")
    draw = ImageDraw.Draw(sheet)
    for i, (slug, n) in enumerate(PICKS):
        x = PAD + (i % COLS) * (W + PAD)
        y = PAD + (i // COLS) * (H + LABEL)
        draw.text((x, y + 4), f"{slug} @ {(int(n) - 1) * 5}s", fill="#847d77", font=font)
        sheet.paste(Image.open(f"reference/stills/{slug}/every5s/{n}.jpg").convert("RGB").resize((W, H)), (x, y + LABEL))
    draw.text((PAD, ref_h + 4), "test frame — averaged style (S02), seed 41", fill="#e6e4dc", font=font)
    sheet.paste(Image.open(test_path).convert("RGB").resize((test_w, test_h)), (PAD, ref_h + LABEL))
    sheet.save(out, quality=90)


if __name__ == "__main__":
    main()
