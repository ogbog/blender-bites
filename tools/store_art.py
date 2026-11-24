"""Compose the store covers from a lesson screenshot.

    python tools/store_art.py docs/img/lesson09-shader-nodes.png

Writes docs/img/store/cover-1280x720.png (Gumroad, GitHub social),
itch-cover-630x500.png and thumb-600x600.png. Fonts: Archivo Black and
DM Sans (both SIL Open Font License).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img" / "store"
TITLE_FONT = "/usr/share/fonts/truetype/google-fonts/ofl/archivoblack/ArchivoBlack-Regular.ttf"
BODY_FONT = "/usr/share/fonts/truetype/google-fonts/ofl/dmsans/DMSans[opsz,wght].ttf"
ORANGE = (255, 140, 31)
INK = (14, 14, 18)
WHITE = (244, 244, 246)
MUTED = (186, 188, 196)


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            f.set_variation_by_axes([14, weight])
        except Exception:
            pass
    return f


def cover_crop(img, w, h, x_bias=0.0, y_bias=0.5):
    s = max(w / img.width, h / img.height)
    im = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x = round((im.width - w) * x_bias)
    y = round((im.height - h) * y_bias)
    return im.crop((x, y, x + w, y + h))


def shade(im, box, direction, alpha_max=238):
    """Dark gradient: direction 'right' fades in toward the right edge, 'bottom' toward the bottom."""
    x0, y0, x1, y1 = box
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    span = (x1 - x0) if direction == "right" else (y1 - y0)
    for i in range(span):
        a = int(alpha_max * min(1.0, (i / span) / 0.45))
        if direction == "right":
            d.line([(x0 + i, y0), (x0 + i, y1)], fill=INK + (a,))
        else:
            d.line([(x0, y0 + i), (x1, y0 + i)], fill=INK + (a,))
    return Image.alpha_composite(im.convert("RGBA"), over)


def text_block(d, x, y, lines, gap=8):
    for txt, f, col in lines:
        d.text((x, y), txt, font=f, fill=col)
        y += f.getbbox(txt)[3] + gap
    return y


def cover(src):
    im = cover_crop(src, 1280, 720, x_bias=0.0)
    im = shade(im, (640, 0, 1280, 720), "right", 242)
    d = ImageDraw.Draw(im)
    x = 838
    y = text_block(d, x, 150, [
        ("Blender", font(TITLE_FONT, 92), WHITE),
        ("Bites", font(TITLE_FONT, 92), ORANGE),
    ], gap=4)
    y = text_block(d, x + 4, y + 26, [
        ("Learn Blender inside Blender.", font(BODY_FONT, 29, 600), WHITE),
        ("15 lessons. 148 bite-size challenges.", font(BODY_FONT, 25, 400), MUTED),
        ("Press F1 on anything to ask what it is.", font(BODY_FONT, 25, 400), MUTED),
    ], gap=12)
    text_block(d, x + 4, 640, [("Free and open source  |  Blender 5", font(BODY_FONT, 22, 500), ORANGE)])
    return im.convert("RGB")


def small(src, w, h, x_bias, title_size, sub):
    im = cover_crop(src, w, h, x_bias=x_bias, y_bias=0.0)
    band = int(h * 0.36)
    im = shade(im, (0, h - band, w, h), "bottom", 236)
    d = ImageDraw.Draw(im)
    tf = font(TITLE_FONT, title_size)
    pad = int(w * 0.055)
    bw = tf.getbbox("Blender ")[2]
    y = h - band + int(band * 0.30)
    d.text((pad, y), "Blender ", font=tf, fill=WHITE)
    d.text((pad + bw, y), "Bites", font=tf, fill=ORANGE)
    sf = font(BODY_FONT, int(title_size * 0.42), 500)
    d.text((pad + 2, y + tf.getbbox("Bb")[3] + 10), sub, font=sf, fill=MUTED)
    return im.convert("RGB")


def thumb(monument_path):
    """Square thumb: title on top, the marble monument (an overlay-free
    viewport render) underneath."""
    mon = Image.open(monument_path).convert("RGB")
    bg = mon.getpixel((8, 8))
    im = Image.new("RGB", (600, 600), bg)
    m = mon.crop((140, 150, 860, 920)).resize((440, 470), Image.LANCZOS)
    im.paste(m, (80, 136))
    d = ImageDraw.Draw(im)
    tf = font(TITLE_FONT, 62)
    bw = tf.getbbox("Blender ")[2]
    total = bw + tf.getbbox("Bites")[2]
    x = (600 - total) // 2
    d.text((x, 26), "Blender ", font=tf, fill=WHITE)
    d.text((x + bw, 26), "Bites", font=tf, fill=ORANGE)
    sf = font(BODY_FONT, 24, 500)
    sub = "15 lessons, inside Blender, free"
    d.text(((600 - sf.getbbox(sub)[2]) // 2, 110), sub, font=sf, fill=MUTED)
    return im


def main(path):
    src = Image.open(path).convert("RGB")
    OUT.mkdir(parents=True, exist_ok=True)
    cover(src).save(OUT / "cover-1280x720.png", optimize=True)
    # Card plus the whole marble monument, then just the monument for the square.
    card_and_monkey = src.crop((80, 36, 1010, 776))
    small(card_and_monkey, 630, 500, 0.5, 58, "Learn Blender inside Blender").save(
        OUT / "itch-cover-630x500.png", optimize=True)
    thumb(ROOT / "docs" / "img" / "monument.png").save(OUT / "thumb-600x600.png", optimize=True)
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "docs/img/lesson09-shader-nodes.png"))
