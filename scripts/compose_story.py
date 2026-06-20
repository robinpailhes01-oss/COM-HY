#!/usr/bin/env python3
"""
Compose un habillage typographique Harmonie sur une image (story 9:16 ou post 4:5).
Respecte 02_VISUAL_IDENTITY.md : serif Cormorant Garamond (titres), Montserrat
(capitales espacées), or champagne #C9A86A, logo discret, voiles dégradés pour
la lisibilité.

Exemple :
  python3 scripts/compose_story.py \
    --base photos/generated/14_juillet_story_base.png \
    --surtitle "14 JUILLET" --title "FEU D'ARTIFICE" --subtitle "EN MER" \
    --footer "SOIRÉE PRIVÉE · SUR RÉSERVATION" \
    --out photos/generated/14_juillet_story_finale.png
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

GOLD = (201, 168, 106)      # #C9A86A — or champagne (charte)
WHITE = (250, 248, 244)
DARK = (12, 14, 24)
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def corm(size, wght=500):
    f = ImageFont.truetype(str(FONTS / "CormorantGaramond-VF.ttf"), size)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


def mont(size, light=True):
    name = "Montserrat-Light.ttf" if light else "Montserrat-Medium.ttf"
    return ImageFont.truetype(str(FONTS / name), size)


def vgrad(w, h, a_top, a_bot):
    g = Image.new("L", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        g.putpixel((0, y), int(a_top + (a_bot - a_top) * t))
    return g.resize((w, h))


def tracked(draw, cx, y, text, font, fill, tracking):
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking
    return total


def fit_size(draw, text, maxw, start, tracking, mk):
    s = start
    while s > 20:
        f = mk(s)
        w = sum(draw.textlength(ch, font=f) for ch in text) + tracking * (len(text) - 1)
        if w <= maxw:
            return f, s
        s -= 4
    return mk(20), 20


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--brand", default="HARMONIE")
    p.add_argument("--brand-sub", default="YACHT")
    p.add_argument("--surtitle", default="")
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--footer", default="")
    p.add_argument("--ratio", default="9:16", choices=["9:16", "4:5"])
    args = p.parse_args()

    W, H = (1080, 1920) if args.ratio == "9:16" else (1080, 1350)
    img = ImageOps.fit(Image.open(args.base).convert("RGB"), (W, H), Image.LANCZOS).convert("RGBA")

    # Voiles dégradés (haut pour le titre, bas pour le pied)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    th = int(H * 0.52)
    top = Image.new("RGBA", (W, th), DARK + (255,)); top.putalpha(vgrad(W, th, 175, 0))
    ov.alpha_composite(top, (0, 0))
    bh = int(H * 0.24)
    bot = Image.new("RGBA", (W, bh), DARK + (255,)); bot.putalpha(vgrad(W, bh, 0, 140))
    ov.alpha_composite(bot, (0, H - bh))
    img = Image.alpha_composite(img, ov)
    d = ImageDraw.Draw(img)
    cx = W // 2

    # — Signature de marque (discrète, en haut)
    y = int(H * 0.055)
    tracked(d, cx, y, args.brand, corm(54, 600), WHITE, 6)
    y += 70
    tracked(d, cx, y, " ".join(args.brand_sub), mont(20), GOLD, 6)
    y += 38
    d.line([(cx - 46, y), (cx + 46, y)], fill=GOLD, width=2)

    # — Bloc titre (remonté dans la zone du voile sombre)
    y = int(H * 0.17)
    if args.surtitle:
        tracked(d, cx, y, args.surtitle, mont(32), GOLD, 14)
        y += 76
    tfont, tsize = fit_size(d, args.title, int(W * 0.80), 160, 4,
                            lambda s: corm(s, 600))
    asc, desc = tfont.getmetrics()
    tracked(d, cx, y, args.title, tfont, WHITE, 4)
    # bas réel des glyphes ≈ y + ascent + descent ; large marge pour aérer
    y += asc + desc + 48
    if args.subtitle:
        tracked(d, cx, y, args.subtitle, mont(30), WHITE, 18)

    # — Pied de page
    if args.footer:
        tracked(d, cx, int(H * 0.945), args.footer, mont(24), WHITE, 6)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, "JPEG", quality=92)
    print("✓", out)


if __name__ == "__main__":
    main()
