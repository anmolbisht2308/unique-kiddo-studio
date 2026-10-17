"""Expressive Kiddo for the comedy formats: faces, body colour, squash/stretch, rotation.

kiddo_layer(s, t, **pose) -> RGBA image with Kiddo centred; use place_kiddo() to composite with transforms.
eyes:  normal | wide | squint | x | heart | happy | closed | star | dizzy
mouth: smile | open | o | pucker | wavy | zigzag | frown | scream
arms:  down | up | wave | cover (hands on cheeks)
"""
import math
from PIL import Image, ImageDraw
from kiddo import u_shape, star_pts

DARK = (55, 45, 70)
CORAL = (255, 112, 98)
STAR = (255, 205, 45)


def _shade(c, f=0.84):
    return tuple(int(v * f) for v in c[:3])


def _heart(d, cx, cy, r, fill):
    d.ellipse([cx - r, cy - r * .9, cx, cy + r * .1], fill=fill)
    d.ellipse([cx, cy - r * .9, cx + r, cy + r * .1], fill=fill)
    d.polygon([(cx - r * .97, cy - r * .25), (cx + r * .97, cy - r * .25), (cx, cy + r)], fill=fill)


def lerp_col(a, b, u):
    u = max(0.0, min(1.0, u))
    return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))


def kiddo_layer(s, t=0.0, eyes="normal", mouth="smile", arms="down", body=CORAL, look=(0.0, 0.0),
                blink=True, cheeks=1.0, star=True):
    k = s / 100.0
    Wc, Hc = int(2.6 * s), int(2.8 * s)
    img = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = Wc / 2, Hc / 2 + 0.1 * s
    p = lambda x, y: (cx + x * k, cy + y * k)
    lw = lambda v: max(2, int(v * k))
    shade = _shade(body)
    hi = tuple(min(255, int(v + (255 - v) * .45)) for v in body)
    # feet
    for fx in (-30, 30):
        d.ellipse([p(fx - 18, 78), p(fx + 18, 92)], fill=shade)
    # arms
    if arms == "up":
        wig = math.sin(t * 14) * 6
        d.ellipse([p(-98, -70 + wig), p(-72, -36 + wig)], fill=shade)
        d.ellipse([p(72, -70 - wig), p(98, -36 - wig)], fill=shade)
    elif arms == "cover":
        d.ellipse([p(-70, 4), p(-44, 36)], fill=shade)
        d.ellipse([p(44, 4), p(70, 36)], fill=shade)
    else:
        d.ellipse([p(-84, 0), p(-60, 34)], fill=shade)
        if arms == "wave":
            a = math.sin(t * 9) * .5
            ax, ay = 72 + math.sin(a) * 8, -5 - math.cos(a * 2) * 2
        else:
            ax, ay = 72, 17
        d.ellipse([p(ax - 12, ay - 17), p(ax + 12, ay + 17)], fill=shade)
    # body
    d.polygon([p(x, y) for x, y in u_shape(3, 4)], fill=shade)
    d.polygon([p(x, y) for x, y in u_shape()], fill=body)
    for lx in (-41, 41):
        d.ellipse([p(lx - 21, -76), p(lx + 21, -34)], fill=body)
    d.ellipse([p(-54, -66), p(-44, -46)], fill=hi)
    # star in the cup
    rot = math.sin(t * 2) * 8
    if not star:
        rot = None
    sy = -40 + math.sin(t * 3) * 3
    if rot is not None:
        d.polygon([p(x, y) for x, y in star_pts(0, sy + 3, 34, rot)], fill=(225, 165, 20))
        d.polygon([p(x, y) for x, y in star_pts(0, sy, 34, rot)], fill=STAR)
        d.ellipse([p(-8, sy - 6), p(-2, sy)], fill=(255, 240, 170))
    # eyes
    lx_, ly_ = look
    is_blink = blink and eyes == "normal" and (t % 3.4) > 3.25
    for side, ex in ((-1, -41), (1, 41)):
        ey = -10
        if eyes in ("normal", "wide", "dizzy"):
            r = 18 if eyes == "wide" else 14
            d.ellipse([p(ex - r, ey - r), p(ex + r, ey + r)], fill=(255, 255, 255), outline=DARK, width=lw(1.5))
            if is_blink:
                d.line([p(ex - 10, ey), p(ex + 10, ey)], fill=DARK, width=lw(4))
            elif eyes == "dizzy":
                for j in range(14):
                    a0 = t * 9 + j * .55
                    rr = 2 + j * .75
                    d.ellipse([p(ex + math.cos(a0) * rr - 1.6, ey + math.sin(a0) * rr - 1.6),
                               p(ex + math.cos(a0) * rr + 1.6, ey + math.sin(a0) * rr + 1.6)], fill=DARK)
            else:
                pr = 5 if eyes == "wide" else 7
                px, py = ex + lx_ * 5, ey + ly_ * 5
                d.ellipse([p(px - pr, py - pr), p(px + pr, py + pr)], fill=DARK)
                d.ellipse([p(px - pr * .45, py - pr * .8), p(px + pr * .25, py - pr * .1)], fill=(255, 255, 255))
        elif eyes == "squint":  # > <
            dx = 10 * side
            d.line([p(ex + dx, ey - 10), p(ex - dx, ey), p(ex + dx, ey + 10)], fill=DARK, width=lw(5), joint="curve")
        elif eyes == "x":
            d.line([p(ex - 9, ey - 9), p(ex + 9, ey + 9)], fill=DARK, width=lw(5))
            d.line([p(ex - 9, ey + 9), p(ex + 9, ey - 9)], fill=DARK, width=lw(5))
        elif eyes == "heart":
            pulse = 1 + .15 * math.sin(t * 12)
            _heart(d, *p(ex, ey - 2), 17 * k * pulse, (240, 50, 90))
        elif eyes == "star":
            d.polygon([p(x, y) for x, y in star_pts(ex, ey, 17, t * 90)], fill=STAR, outline=DARK)
        elif eyes == "happy":  # ^ ^
            d.arc([p(ex - 13, ey - 8), p(ex + 13, ey + 16)], 200, 340, fill=DARK, width=lw(5))
        elif eyes == "closed":
            d.arc([p(ex - 12, ey - 14), p(ex + 12, ey + 6)], 20, 160, fill=DARK, width=lw(5))
    # cheeks
    if cheeks > 0:
        cc = (255, 150, 165) if cheeks <= 1 else (255, 70, 70)
        for chx in (-46, 46):
            d.ellipse([p(chx - 9 * cheeks, 12), p(chx + 9 * cheeks, 22 + 2 * (cheeks - 1))], fill=cc)
    # mouth
    if mouth == "smile":
        d.arc([p(-22, 40), p(22, 70)], 20, 160, fill=DARK, width=lw(5))
    elif mouth == "open":
        d.pieslice([p(-26, 36), p(26, 80)], 0, 180, fill=DARK)
        d.ellipse([p(-12, 60), p(12, 78)], fill=(255, 120, 140))
    elif mouth == "scream":
        o = 3 * math.sin(t * 30)
        d.ellipse([p(-20, 36 - o), p(20, 84 + o)], fill=DARK)
        d.ellipse([p(-11, 64), p(11, 80)], fill=(255, 120, 140))
    elif mouth == "o":
        d.ellipse([p(-11, 46), p(11, 72)], fill=DARK)
    elif mouth == "pucker":
        d.ellipse([p(-8, 52), p(8, 66)], fill=(255, 150, 160), outline=DARK, width=lw(4))
    elif mouth == "frown":
        d.arc([p(-20, 52), p(20, 80)], 200, 340, fill=DARK, width=lw(5))
    elif mouth in ("wavy", "zigzag"):
        pts = []
        for j in range(13):
            x = -26 + j * 52 / 12
            if mouth == "wavy":
                y = 58 + 5 * math.sin(j * 1.3 + t * 10)
            else:
                y = 58 + (6 if j % 2 else -6) * (1 if int(t * 16) % 2 else .5)
            pts.append(p(x, y))
        d.line(pts, fill=DARK, width=lw(5), joint="curve")
    return img


def place_kiddo(img, layer, x, y, sx=1.0, sy=1.0, rot=0.0):
    """Composite a kiddo layer so that its feet stay planted at (x, y) under squash/stretch."""
    w, h = layer.size
    nw, nh = max(2, int(w * sx)), max(2, int(h * sy))
    L = layer.resize((nw, nh), Image.BICUBIC) if (nw, nh) != (w, h) else layer
    if abs(rot) > .2:
        L = L.rotate(rot, resample=Image.BICUBIC, expand=True)
    # feet sit 1.02*s below the layer centre, i.e. 0.364 of the layer height
    foot_off = 0.364 * nh
    img.alpha_composite(L, (int(x - L.width / 2), int(y - foot_off - L.height / 2)))
