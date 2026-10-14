"""Kiddo: an original mascot for Unique Kiddo — a chunky letter-U buddy holding a star."""
import math

DARK = (55, 45, 70)
BODY = (255, 112, 98)
SHADE = (214, 78, 70)
STAR = (255, 205, 45)

def _P(cx, cy, k):
    return lambda x, y: (cx + x * k, cy + y * k)

def u_shape(ox=0, oy=0):
    pts = [(-62 + ox, -55 + oy), (-62 + ox, 22 + oy)]
    for i in range(37):  # outer arc, left -> bottom -> right
        a = math.radians(180 - i * 5)
        pts.append((math.cos(a) * 62 + ox, 22 + math.sin(a) * 62 + oy))
    pts += [(62 + ox, -55 + oy), (20 + ox, -55 + oy), (20 + ox, 22 + oy)]
    for i in range(37):  # inner arc, right -> bottom -> left
        a = math.radians(i * 5)
        pts.append((math.cos(a) * 20 + ox, 22 + math.sin(a) * 20 + oy))
    pts.append((-20 + ox, -55 + oy))
    return pts

def star_pts(cx, cy, r, rot=0):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.radians(-90 + i * 36 + rot)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts

def kiddo(d, cx, cy, s, t=0.0, wave=False, blink_ok=True):
    if s <= 0.01:
        return
    k = s / 100.0
    bob = math.sin(t * 4) * 3
    p = _P(cx, cy + bob * k, k)
    # feet
    for fx in (-30, 30):
        d.ellipse([p(fx - 18, 78), p(fx + 18, 92)], fill=SHADE)
    # arms
    wang = math.sin(t * 9) * 0.5 if wave else 0.0
    d.ellipse([p(-84, 0), p(-60, 34)], fill=SHADE)
    ax, ay = 72 + math.sin(wang) * 8, 17 - (22 if wave else 0) - math.cos(wang * 2) * 2
    d.ellipse([p(ax - 12, ay - 17), p(ax + 12, ay + 17)], fill=SHADE)
    # body: shadow + main
    d.polygon([p(x, y) for x, y in u_shape(3, 4)], fill=SHADE)
    d.polygon([p(x, y) for x, y in u_shape()], fill=BODY)
    for lx in (-41, 41):  # rounded leg tops
        d.ellipse([p(lx - 21, -76), p(lx + 21, -34)], fill=BODY)
    # shine
    d.ellipse([p(-54, -66), p(-44, -46)], fill=(255, 170, 160))
    # star held in the cup
    rot = math.sin(t * 2) * 8
    sy = -40 + math.sin(t * 3) * 3
    d.polygon([p(x, y) for x, y in star_pts(0, sy + 3, 34, rot)], fill=(225, 165, 20))
    d.polygon([p(x, y) for x, y in star_pts(0, sy, 34, rot)], fill=STAR)
    d.ellipse([p(-8, sy - 6), p(-2, sy)], fill=(255, 240, 170))
    # face: eyes on the legs, smile on the bottom curve
    blink = blink_ok and (t % 3.4) > 3.25
    for ex in (-41, 41):
        d.ellipse([p(ex - 14, -24), p(ex + 14, 4)], fill=(255, 255, 255))
        if blink:
            d.line([p(ex - 10, -10), p(ex + 10, -10)], fill=DARK, width=max(2, int(4 * k)))
        else:
            d.ellipse([p(ex - 7, -16), p(ex + 7, 0)], fill=DARK)
            d.ellipse([p(ex - 3, -14), p(ex + 2, -9)], fill=(255, 255, 255))
    for chx in (-46, 46):
        d.ellipse([p(chx - 9, 12), p(chx + 9, 22)], fill=(255, 160, 170))
    d.arc([p(-22, 40), p(22, 70)], 20, 160, fill=DARK, width=max(2, int(5 * k)))
