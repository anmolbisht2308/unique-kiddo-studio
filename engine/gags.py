"""Kiddo Toons: wordless 10-12 s slapstick loops (general audience).

Usage:  python3 engine/gags.py episodes/gag01_x.json [--preview t1 t2 ...]
Episode: {"id": "gag01", "format": "gag", "gag": "door" | "sneeze" | "bubble" | "spring" | "chair", "seo": {...}}
Each gag is a hand-timed script below; the last frame lines up with the first so the Short loops.
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import render as R  # noqa: E402
import doors as D  # noqa: E402  (mix(), srt())
import tts  # noqa: E402
from kiddo_fx import kiddo_layer, place_kiddo, lerp_col, CORAL  # noqa: E402
from kiddo import star_pts  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 44100
DARK = (55, 45, 70)
S = 350; K = S / 100
FEET = 1440
FLOOR = 1150
clamp = R.clamp


def ease(x):
    x = clamp(x); return x * x * (3 - 2 * x)


def ease_in(x):
    x = clamp(x); return x * x


def seg(t, a, b):
    return clamp((t - a) / (b - a))


# ------------------------------------------------------------------ timeline
class GTL:
    def __init__(self, ep):
        self.ep = ep
        self.kid = tts.voice(ep.get("kiddo_voice", {"af_bella": 1.0}))
        self.clips, self.sfx, self.subs = [], [], []

    def vocal(self, t, text, pitch=1.25):
        a, sr = tts.tts(text, self.kid, 1.0)
        x = R.resample(a.astype(float), sr * pitch)
        nz = np.where(np.abs(x) > .01)[0]
        if len(nz): x = x[max(0, nz[0] - 400): nz[-1] + 800]
        self.clips.append((t, x, "kid"))
        self.subs.append((t, t + len(x) / SR, f"[Kiddo: {text}]"))

    def fx(self, t, name):
        self.sfx.append((t, name))


# ------------------------------------------------------------------ drawing helpers
def background(img, wall=(255, 228, 196), floor=(236, 196, 150)):
    d = ImageDraw.Draw(img)
    for y in range(0, FLOOR, 8):  # soft vertical gradient
        u = y / FLOOR
        d.rectangle([0, y, W, y + 8], fill=lerp_col(tuple(min(255, c + 18) for c in wall), wall, u))
    d.rectangle([0, FLOOR, W, H], fill=floor)
    d.rectangle([0, FLOOR - 14, W, FLOOR + 4], fill=tuple(max(0, c - 60) for c in wall))
    for k in range(-5, 6):
        d.line([(W / 2 + k * 110, FLOOR), (W / 2 + k * 330, H)], fill=tuple(max(0, c - 18) for c in floor), width=4)
    return d


def shadow(img, x, lift=0.0, w=180):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = max(.25, 1 - lift / 900)
    d.ellipse([x - w * f, FEET - 22 * f, x + w * f, FEET + 22 * f], fill=(60, 40, 30, int(70 * f)))
    img.alpha_composite(ov)


def kid(img, t, x, y=FEET, sx=1., sy=1., rot=0., **face):
    layer = kiddo_layer(S, t, **face)
    place_kiddo(img, layer, x, y, sx, sy, rot)


def shake_img(img, amt, t):
    if amt < .5: return img
    sx_, sy_ = int(amt * math.sin(t * 61)), int(amt * math.cos(t * 53))
    base = Image.new("RGBA", (W, H), (255, 228, 196, 255)); base.paste(img, (sx_, sy_))
    return base


def sweat(d, x, top, t, n=3):
    for j in range(n):
        ph = (t * 2.2 + j / n) % 1
        side = -1 if j % 2 else 1
        px = x + side * (120 + 120 * ph); py = top + 30 - 90 * math.sin(math.pi * ph) + 60 * ph
        d.ellipse([px - 11, py - 18, px + 11, py + 14], fill=(110, 185, 245), outline=DARK, width=3)


def stars_ring(d, x, y, t, n=3, r=130):
    for j in range(n):
        a = t * 5 + j * 2 * math.pi / n
        d.polygon(star_pts(x + math.cos(a) * r, y + math.sin(a) * r * .3, 28, t * 200), fill=(255, 205, 45), outline=DARK)


# ================================================================== GAG 1: push / pull door
DX0, DX1, DTOP = 620, 1000, FEET - 880
KNOB = (650, FEET - 75 * K)


def door_draw(img, ang, sign_word, flip):
    d = ImageDraw.Draw(img)
    d.rectangle([DX0 - 26, DTOP - 26, DX1 + 26, FEET + 8], fill=(150, 96, 60))
    d.rectangle([DX0 - 12, DTOP - 12, DX1 + 12, FEET + 8], fill=(196, 132, 84))
    d.rectangle([DX0, DTOP, DX1, FEET + 8], fill=(55, 40, 80))
    th = math.radians(84 * ang)
    w = DX1 - DX0
    fx = DX1 - w * math.cos(th)
    grow = 1 + .18 * math.sin(th)
    h = FEET + 8 - DTOP
    pts = [(DX1, DTOP), (fx, DTOP - h * (grow - 1) / 2), (fx, FEET + 8 + h * (grow - 1) * .1), (DX1, FEET + 8)]
    col = tuple(int(c * (1 - .35 * math.sin(th))) for c in (96, 160, 230))
    d.polygon(pts, fill=col, outline=DARK)
    if ang < .3:
        m = 30
        for y0, y1 in ((DTOP + m, DTOP + h * .42), (DTOP + h * .5, FEET - m)):
            d.rounded_rectangle([DX0 + m, y0, DX1 - m, y1], radius=16, fill=(126, 184, 240))
        d.ellipse([KNOB[0] - 20, KNOB[1] - 20, KNOB[0] + 20, KNOB[1] + 20], fill=(255, 205, 45), outline=DARK, width=4)
        # sign
        cx, cy = (DX0 + DX1) / 2, DTOP + 210
        sc = abs(math.cos(math.pi * flip))
        word = sign_word[0] if flip < .5 else sign_word[1]
        hw = 120 * max(sc, .04)
        d.line([(cx - 60 * sc, cy - 60), (cx, cy - 110), (cx + 60 * sc, cy - 60)], fill=DARK, width=5)
        d.rounded_rectangle([cx - hw, cy - 58, cx + hw, cy + 58], radius=14, fill=(255, 255, 255), outline=DARK, width=6)
        if sc > .25:
            f = R.font(int(78 * sc))
            d.text((cx, cy), word, font=f, fill=(225, 60, 50) if word == "PUSH" else (40, 120, 220), anchor="mm")


def gag_door(tl):
    T = 10.8
    tl.vocal(.15, "Hmmph!", 1.3); tl.fx(.3, "creak")
    tl.vocal(1.3, "Hnnnngh!", 1.3); tl.fx(1.5, "creak"); tl.fx(1.9, "creak")
    tl.fx(3.25, "whoosh"); tl.fx(3.6, "ding")
    tl.fx(4.45, "whoosh"); tl.fx(4.55, "slide_down"); tl.fx(5.1, "bonk")
    tl.vocal(6.35, "Ta-da!", 1.3)
    tl.fx(6.85, "whoosh"); tl.fx(7.08, "big_pop"); tl.fx(7.1, "bonk")
    tl.fx(8.45, "boing")
    tl.fx(8.85, "whoosh"); tl.fx(9.2, "ding")
    tl.fx(10.2, "pop")
    tl.duration = T

    def frame(t):
        img = Image.new("RGBA", (W, H)); background(img)
        # door angle
        ang = 0.0
        if 4.45 <= t < 6.85: ang = ease((t - 4.45) / .25)
        elif 6.85 <= t < 7.08: ang = 1 - ease_in((t - 6.85) / .23)
        flip = 0.0; words = ("PULL", "PUSH")
        if 3.2 <= t < 8.8: flip = ease((t - 3.2) / .4)
        if t >= 8.8: words = ("PUSH", "PULL"); flip = ease((t - 8.8) / .4)
        door_draw(img, ang, words, flip)
        x, y, sx, sy, rot = 400., FEET, 1., 1., 0.
        P = dict(eyes="squint", mouth="zigzag", arms="down", look=(0, 0))
        arm = False; shake = 0; sweaty = False; dizzy = False
        if t < 1.1:
            p = math.sin(math.pi * t / 1.1); x -= 40 * p; rot = 8 * p; sx = 1 - .1 * p; sy = 1 + .1 * p; arm = True
        elif t < 1.25:
            arm = True
        elif t < 2.6:
            p = math.sin(math.pi * (t - 1.25) / 1.35); x -= 120 * p; rot = 16 * p; sx = 1 - .18 * p; sy = 1 + .2 * p
            arm = True; shake = 6 * p; sweaty = True
        elif t < 3.7:
            P.update(eyes="normal", mouth="frown", look=(0, .25))
        elif t < 4.3:
            P.update(eyes="wide", mouth="o", look=(.7, -.8))
        elif t < 4.55:
            q = ease((t - 4.3) / .25); x = 400 + 96 * q; rot = -10 * q; arm = True
            P.update(eyes="normal", mouth="smile")
        elif t < 5.1:
            q = ease_in((t - 4.55) / .55); x = 496 + 214 * q; rot = -10 - 80 * q
            P.update(eyes="wide", mouth="scream", arms="up")
        elif t < 5.8:
            x = 710; rot = -90; P.update(eyes="x", mouth="wavy")
            shake = 10 * math.exp(-(t - 5.1) * 8)
        elif t < 6.4:
            q = ease((t - 5.8) / .6); x = 710; rot = -90 * (1 - q); P.update(eyes="closed", mouth="smile")
        elif t < 7.1:
            x = 710; j = abs(math.sin((t - 6.4) * 9)); y = FEET - 40 * j
            P.update(eyes="happy", mouth="open", arms="up")
        elif t < 8.45:
            x = 710; wob = math.sin((t - 7.1) * 18) * math.exp(-(t - 7.1) * 2)
            sx = .22 + .04 * wob; sy = 1.12 - .03 * wob; dizzy = True
            P.update(eyes="dizzy", mouth="wavy"); shake = 9 * math.exp(-(t - 7.1) * 6)
        elif t < 8.8:
            q = (t - 8.45) / .35; x = 710
            ov = math.sin(q * math.pi * 2.5) * math.exp(-q * 3)
            sx = .22 + .78 * ease(q * 1.6) + .2 * ov; sy = 1.12 - .12 * ease(q * 1.6) - .15 * ov
            P.update(eyes="wide", mouth="o")
        elif t < 9.9:
            x = 710; P.update(eyes="normal", mouth="frown", look=(0, .25) if t > 9.3 else (.6, -.8))
        else:
            q = ease((t - 9.9) / .7); x = 710 - 286 * q; y = FEET - 18 * abs(math.sin((t - 9.9) * 12)) * (1 - q)
            P.update(eyes="squint" if t > 10.5 else "normal", mouth="zigzag" if t > 10.5 else "smile")
            arm = t > 10.45
        shadow(img, x, FEET - y)
        kid(img, t, x, y, sx, sy, rot, **P)
        d = ImageDraw.Draw(img)
        if arm:
            sh = (x + 62 * K * sx * math.cos(math.radians(rot)), FEET - 92 * K * sy + 17 * K * sy - 62 * K * math.sin(math.radians(rot)))
            d.line([sh, KNOB], fill=(214, 78, 70), width=36)
            d.ellipse([KNOB[0] - 30, KNOB[1] - 30, KNOB[0] + 30, KNOB[1] + 30], fill=(214, 78, 70))
        if sweaty:
            sweat(d, x, FEET - 168 * K * sy, t)
        if dizzy:
            stars_ring(d, x, FEET - 168 * K * sy - 30, t, r=110)
        return shake_img(img, shake, t)
    return frame


# ================================================================== GAG 2: sneeze
POT = (840, FEET)
STEM_TOP = (840, FEET - 430)


def pot_draw(d, t, bend=0.0):
    x, y = POT
    d.polygon([(x - 105, y - 170), (x + 105, y - 170), (x + 78, y + 8), (x - 78, y + 8)], fill=(200, 105, 70), outline=DARK)
    d.rectangle([x - 118, y - 196, x + 118, y - 160], fill=(214, 120, 82), outline=DARK, width=4)
    top = (STEM_TOP[0] + 40 * bend, STEM_TOP[1] + 20 * bend)
    d.line([(x, y - 190), (x + 10 * bend, y - 320), top], fill=(70, 160, 70), width=16, joint="curve")
    for sgn in (-1, 1):
        lx, ly = x + sgn * 45, y - 290
        d.ellipse([lx - 45, ly - 18, lx + 45, ly + 18], fill=(90, 185, 85), outline=DARK, width=3)
    return top


def gag_sneeze(tl):
    T = 10.5
    tl.vocal(.85, "Ah...", 1.15); tl.vocal(1.65, "Ah...", 1.3); tl.vocal(2.45, "Ahhh...", 1.45)
    tl.vocal(4.15, "CHOO!", 1.25); tl.fx(4.15, "whoosh"); tl.fx(4.18, "boing")
    tl.fx(5.6, "crash")
    tl.fx(6.2, "slide_down"); tl.fx(6.9, "ding")
    tl.fx(9.5, "boing"); tl.fx(9.8, "pop"); tl.fx(9.85, "sparkle")
    tl.duration = T
    petals = [(math.cos(a) * 1, math.sin(a) * 1) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]

    def frame(t):
        img = Image.new("RGBA", (W, H)); background(img, wall=(214, 238, 222), floor=(226, 200, 160))
        d = ImageDraw.Draw(img)
        bend = 0.0
        if 4.15 <= t < 6.0: bend = math.exp(-(t - 4.15) * 3) * math.sin((t - 4.15) * 14)
        top = pot_draw(d, t, bend)
        flower_on = t < 4.15 or t >= 9.8
        if flower_on:
            sc = R.pop(t, 9.8, .4) if t >= 9.8 else 1
            R.paste_emoji(img, "🌻", top[0], top[1] - 40, 250 * sc)
        elif t < 7.5:
            for j, (cx, cy) in enumerate(petals):  # petals blown off
                u = t - 4.15
                px = top[0] + cx * 70 + u * (360 + 40 * j % 120) - 20 * u * u
                py = top[1] - 40 + cy * 70 - 220 * u + 260 * u * u * .6 + 30 * math.sin(u * 5 + j)
                if py < FEET:
                    d.ellipse([px - 26, py - 12, px + 26, py + 12], fill=(255, 200, 40), outline=(200, 140, 20), width=3)
        # star travelling: flies in, lands on stem, then hops back to kiddo
        star_on_kid = t < 4.15 or t >= 9.85
        if 6.2 <= t < 9.5:
            q = ease((t - 6.2) / .7)
            sx_, sy_ = -100 + (top[0] + 100) * q, 900 + (top[1] - 40 - 900) * q - 380 * math.sin(math.pi * q)
            d.polygon(star_pts(sx_, sy_, 70, t * 90), fill=(255, 205, 45), outline=DARK)
        elif 9.5 <= t < 9.85:
            q = ease((t - 9.5) / .35)
            ex, ey = 420, FEET - 92 * K - 40 * K
            sx_, sy_ = top[0] + (ex - top[0]) * q, top[1] - 40 + (ey - top[1] + 40) * q - 200 * math.sin(math.pi * q)
            d.polygon(star_pts(sx_, sy_, 70 - 30 * q, t * 360), fill=(255, 205, 45), outline=DARK)
        # kiddo
        x, y, sx, sy, rot = 420., FEET, 1., 1., 0.
        P = dict(eyes="closed", mouth="smile", star=star_on_kid)
        shake = 0; leaves = False; speed = False
        if t < .75 or t >= 9.9:
            rot = -7 * (ease((t - 9.9) / .4) if t >= 9.9 else 1)
        elif t < 3.0:
            n = min(3, int((t - .75) / .8) + 1); ph = ((t - .75) % .8) / .8
            amp = .12 * (n - 1) + .12 * ease(ph)
            sx = 1 + amp; sy = 1 + amp * .9; rot = -7 + 19 * clamp((t - .75) / 2.25)
            P.update(eyes="squint", mouth="o", body=lerp_col(CORAL, (255, 140, 150), amp * 2))
        elif t < 3.6:
            q = ease((t - 3.0) / .6); a = .36 * (1 - q); sx = 1 + a; sy = 1 + a * .9; rot = 12 * (1 - q)
            P.update(eyes="normal", mouth="smile", look=(0, .25))
        elif t < 4.15:
            P.update(eyes="happy", mouth="smile", look=(0, .25))
        elif t < 4.6:
            q = ease_in((t - 4.15) / .45); x = 420 - 1000 * q; rot = 720 * q
            P.update(eyes="squint", mouth="open"); shake = 12; speed = True
        elif t < 7.2:
            x = -600; shake = 10 * math.exp(-(t - 5.6) * 6) if t >= 5.6 else 0
        elif t < 8.9:
            q = (t - 7.2) / 1.7; x = -200 + 620 * ease(q); y = FEET - 20 * abs(math.sin(t * 11))
            rot = 9 * math.sin(t * 6); leaves = True
            P.update(eyes="dizzy", mouth="wavy", star=False)
        elif t < 9.5:
            leaves = True; P.update(eyes="wide", mouth="o", look=(.8, -.6), star=False)
        elif t < 9.9:
            P.update(eyes="happy", mouth="open", star=t >= 9.85)
        if x > -400:
            shadow(img, x, FEET - y)
            kid(img, t, x, y, sx, sy, rot, **P)
        d = ImageDraw.Draw(img)
        if t < .75 or t >= 9.95:  # pollen drifting to kiddo
            for j in range(8):
                ph = (t * .9 + j / 8) % 1
                px = top[0] - 60 - (top[0] - 560) * ph; py = top[1] - 20 + (FEET - 300 - top[1]) * ph + 15 * math.sin(ph * 9 + j)
                d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(255, 215, 60), outline=(210, 160, 20))
        if speed:
            for j in range(6):
                yy = FEET - 480 + j * 70
                d.line([(x + 250, yy), (x + 650, yy)], fill=(255, 255, 255), width=14)
        if leaves:
            R.paste_emoji(img, "🍃", x - 60, FEET - 168 * K - 20, 110)
            R.paste_emoji(img, "🍂", x + 70, FEET - 168 * K - 5, 90)
        return shake_img(img, shake, t)
    return frame


# ================================================================== GAG 3: bubble gum
LIFT = 470


def gag_bubble(tl):
    T = 11.0
    for k in range(4):
        tl.fx(.1 + k * .3, "chew")
    tl.fx(1.3, "stretch")
    tl.fx(3.6, "float_up"); tl.vocal(3.8, "Wheee!", 1.35)
    tl.fx(6.2, "buzz")
    tl.fx(7.0, "big_pop"); tl.vocal(7.2, "Uh oh.", 1.25)
    tl.fx(7.7, "slide_down"); tl.fx(8.15, "splat"); tl.fx(8.17, "bonk")
    tl.fx(9.5, "pop")
    for k in range(3):
        tl.fx(10.15 + k * .3, "chew")
    tl.duration = T

    def frame(t):
        img = Image.new("RGBA", (W, H)); background(img, wall=(226, 230, 255), floor=(214, 196, 170))
        x, y, sx, sy, rot = 540., FEET, 1., 1., 0.
        P = dict(eyes="happy", mouth="smile")
        r = 0.0; gumface = 0.0; shake = 0; burst = None
        chewing = t < 1.3 or t >= 10.15
        if chewing:
            P["mouth"] = "pucker" if int(t / .15) % 2 else "smile"; y = FEET - 6 * abs(math.sin(t * 7))
        elif t < 3.6:
            q = ease((t - 1.3) / 2.3); r = 20 + 230 * q + 6 * math.sin(t * 13)
            P.update(mouth="pucker", eyes="wide" if t > 3.0 else "happy")
        elif t < 7.0:
            q = ease((t - 3.6) / 3.0); r = 250 + 6 * math.sin(t * 5); y = FEET - LIFT * q
            rot = 5 * math.sin(t * 2.4); P.update(eyes="happy", mouth="open", arms="up")
            if t > 6.3: P.update(eyes="wide", mouth="o", look=(.9, -.5))
        elif t < 7.7:
            y = FEET - LIFT; burst = t - 7.0; gumface = 1
            P.update(eyes="wide", mouth="o", look=(0, .25))
        elif t < 8.15:
            q = ease_in((t - 7.7) / .45); y = FEET - LIFT * (1 - q); gumface = 1
            P.update(eyes="wide", mouth="scream", arms="up"); sy = 1 + .15 * q; sx = 1 - .1 * q
        elif t < 9.3:
            u = t - 8.15; b = math.exp(-u * 6) * math.cos(u * 22)
            sy = 1 - .45 * b if u < .5 else 1; sx = 1 + .4 * b if u < .5 else 1
            shake = 12 * math.exp(-u * 8); gumface = 1
            if u > .45: x = 540 + 14 * math.sin(t * 40)
            P.update(eyes="closed", mouth="frown")
        elif t < 9.6:
            gumface = 1 - ease((t - 9.3) / .3); P.update(eyes="wide", mouth="o")
        elif t < 10.15:
            P.update(eyes="normal", mouth="smile", look=(0, .25))
        shadow(img, x, FEET - y)
        kid(img, t, x, y, sx, sy, rot, **P)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        mx, my = x, y - 37 * K * sy
        if r > 0:
            cx, cy = mx + r * .55, my - r * .45
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 140, 195, 235), outline=(200, 70, 140, 255), width=6)
            d.ellipse([cx - r * .55, cy - r * .7, cx - r * .15, cy - r * .35], fill=(255, 255, 255, 170))
        if burst is not None and burst < .6:
            cx, cy = mx + 140, my - 110
            for j in range(9):
                a = j * .7; dd = 120 + 420 * burst
                px, py = cx + math.cos(a) * dd, cy + math.sin(a) * dd
                rr = 40 * (1 - burst)
                d.ellipse([px - rr, py - rr * .7, px + rr, py + rr * .7], fill=(255, 140, 195, int(255 * (1 - burst / .6))))
        if gumface > 0:
            fx_, fy = x, y - (92 + 10) * K * sy
            g = gumface
            for dx_, dy_, rr in ((-110, 0, 95), (110, 0, 95), (0, 40, 120), (-40, -60, 80), (60, 80, 70)):
                d.ellipse([fx_ + dx_ * g - rr * g, fy + dy_ * g - rr * g, fx_ + dx_ * g + rr * g, fy + dy_ * g + rr * g],
                          fill=(255, 140, 195, 240))
        img.alpha_composite(ov)
        if 6.0 <= t < 7.05:  # bird swoops in and pecks the bubble
            q = ease((t - 6.0) / 1.0)
            bx = 1250 - (1250 - (mx + 250 * 1.3)) * q; by = (FEET - LIFT - 350) - 120 * math.sin(math.pi * q)
            flap = 1 + .25 * math.sin(t * 30)
            e = R.emoji_img("🐦", 170).resize((170, int(170 * flap)))
            img.alpha_composite(e, (int(bx - 85), int(by - 85 * flap)))
        elif 7.05 <= t < 8.0:
            q = (t - 7.05) / .95
            R.paste_emoji(img, "🐦", (mx + 320) - 900 * q, (FEET - 1050) - 300 * q, 150)
        return shake_img(img, shake, t)
    return frame


# ================================================================== GAG 4: floor spring
SPX, SPR = 660, 175  # spring x, rest height


def spring_draw(d, x, h, tilt=0.0):
    base, top = FEET + 6, FEET + 6 - h
    d.rounded_rectangle([x - 115, base - 22, x + 115, base + 8], radius=8, fill=(120, 125, 140), outline=DARK, width=4)
    n = 6; pts = []
    for j in range(n * 2 + 1):
        yy = base - 18 - (h - 36) * j / (n * 2)
        pts.append((x + (85 if j % 2 else -85) + tilt * (j / (n * 2)) * 40, yy))
    d.line(pts, fill=DARK, width=24, joint="curve")
    d.line(pts, fill=(190, 198, 214), width=15, joint="curve")
    tx = x + tilt * 40
    d.rounded_rectangle([tx - 115, top - 8, tx + 115, top + 22], radius=8, fill=(225, 70, 60), outline=DARK, width=4)


def gag_spring(tl):
    T = 11.0
    tl.fx(1.55, "boing"); tl.fx(1.95, "boing")
    tl.vocal(2.25, "Hehehe!", 1.3)
    tl.fx(2.8, "boing"); tl.fx(2.82, "whoosh")
    tl.fx(3.25, "bonk"); tl.fx(3.3, "crash")
    tl.fx(4.2, "slide_down"); tl.vocal(4.25, "Aaah!", 1.3)
    tl.fx(4.62, "boing"); tl.fx(4.64, "whoosh")
    tl.fx(5.05, "bonk")
    tl.fx(5.45, "boing"); tl.fx(5.75, "boing")
    tl.fx(5.9, "slide_down"); tl.fx(6.3, "splat"); tl.fx(6.32, "bonk")
    tl.fx(7.65, "pop")
    tl.fx(8.35, "boing")
    tl.vocal(8.9, "Hmph!", 1.25)
    tl.fx(9.55, "boing"); tl.fx(9.95, "boing")
    tl.fx(10.3, "ding")
    tl.duration = T
    rest = FEET - SPR

    def frame(t):
        img = Image.new("RGBA", (W, H)); background(img, wall=(255, 236, 200), floor=(222, 190, 150))
        d = ImageDraw.Draw(img)
        # ceiling cracks after the bonks
        if t >= 3.25 and t < 10.9:
            for k_, cx in enumerate((640, 600)):
                if t >= (3.25 if k_ == 0 else 5.05):
                    d.line([(cx - 60, 0), (cx - 20, 40), (cx + 10, 15), (cx + 50, 60), (cx + 80, 20)], fill=DARK, width=7)
        # spring state
        sx_, h, tilt = SPX, SPR, 0.0
        if 1.55 <= t < 2.2:
            u = (t - 1.55) % .4; h = SPR - 45 * math.sin(math.pi * clamp(u / .15)) if u < .15 else SPR
        elif 2.2 <= t < 2.8:
            h = SPR - 110 * ease((t - 2.2) / .6)
        elif 2.8 <= t < 4.2:
            h = SPR + 50 * math.exp(-(t - 2.8) * 4) * math.sin((t - 2.8) * 30); tilt = .6 * math.exp(-(t - 2.8) * 3) * math.sin((t - 2.8) * 18)
        elif 4.55 <= t < 4.62:
            h = SPR - 120 * ease((t - 4.55) / .07)
        elif 4.62 <= t < 5.4:
            h = SPR + 50 * math.exp(-(t - 4.62) * 4) * math.sin((t - 4.62) * 30)
        elif 5.4 <= t < 5.9:  # spring sneaks away (two hops)
            q = (t - 5.4) / .5; sx_ = SPX + 300 * ease(q); h = SPR + 25 * abs(math.sin(q * 2 * math.pi))
        elif 5.9 <= t < 9.5:
            sx_ = SPX + 300
            if 8.2 <= t < 8.6: h = SPR + 40 * math.sin(math.pi * (t - 8.2) / .4); tilt = -.5 * math.sin(math.pi * (t - 8.2) / .4)
        elif 9.5 <= t < 10.3:  # spring sneaks back
            q = (t - 9.5) / .8; sx_ = SPX + 300 * (1 - ease(q)); h = SPR + 30 * abs(math.sin(q * 2 * math.pi))
        spring_y_off = 0
        if 5.4 <= t < 5.9 or 9.5 <= t < 10.3:
            q = ((t - 5.4) / .5) if t < 5.9 else ((t - 9.5) / .8)
            spring_y_off = -70 * abs(math.sin(q * 2 * math.pi))
        # kiddo
        x, y, sx, sy, rot = 260., FEET, 1., 1., 0.
        P = dict(eyes="normal", mouth="smile", look=(.6, .3))
        shake = 0; speed = False; dizzy = False; show = True
        if t < 1.0:
            y = FEET - 8 * abs(math.sin(t * 6))
            P.update(eyes="wide" if t > .5 else "normal", mouth="o" if t > .5 else "smile")
        elif t < 1.55:
            q = (t - 1.0) / .55; x = 260 + (SPX - 260) * ease(q); y = FEET + (rest - FEET) * q - 180 * math.sin(math.pi * q)
            P.update(eyes="happy", mouth="open", arms="up")
        elif t < 2.2:
            x = SPX; u = (t - 1.55) % .4; hop = 70 * math.sin(math.pi * clamp((u - .15) / .25)) if u >= .15 else 0
            y = FEET - h - hop; P.update(eyes="happy", mouth="open", arms="up")
        elif t < 2.8:
            x = SPX; y = FEET - h; q = ease((t - 2.2) / .6); sx = 1 + .15 * q; sy = 1 - .2 * q
            P.update(eyes="squint", mouth="smile", arms="down")
        elif t < 3.1:
            x = SPX; q = ease_in((t - 2.8) / .3); y = FEET - SPR - 2200 * q; sx = .75; sy = 1.4
            P.update(eyes="wide", mouth="scream", arms="up"); speed = True
        elif t < 4.2:
            show = False; shake = 14 * math.exp(-(t - 3.25) * 7) if t >= 3.25 else 0
        elif t < 4.62:
            x = SPX; q = ease_in((t - 4.2) / .4); y = -300 + (FEET - SPR + 300) * q; sx = .85; sy = 1.2
            P.update(eyes="x", mouth="scream", arms="up")
        elif t < 4.92:
            x = SPX; q = ease_in((t - 4.62) / .3); y = FEET - SPR - 2200 * q; sx = .75; sy = 1.4
            P.update(eyes="wide", mouth="scream", arms="up"); speed = True
        elif t < 5.9:
            show = False; shake = 14 * math.exp(-(t - 5.05) * 7) if t >= 5.05 else 0
        elif t < 6.3:
            x = SPX; q = ease_in((t - 5.9) / .4); y = -300 + (FEET + 300) * q; sx = .85; sy = 1.2
            P.update(eyes="wide", mouth="scream", arms="up", look=(.8, .4))
        elif t < 7.65:
            x = SPX; u = t - 6.3; wob = math.sin(u * 18) * math.exp(-u * 2)
            sx = 1.7 + .08 * wob; sy = .28 - .03 * wob; dizzy = True
            P.update(eyes="dizzy", mouth="wavy"); shake = 16 * math.exp(-u * 7)
        elif t < 8.0:
            x = SPX; q = (t - 7.65) / .35; ov = math.sin(q * math.pi * 2.5) * math.exp(-q * 3)
            sx = 1.7 - .7 * ease(q * 1.6) - .2 * ov; sy = .28 + .72 * ease(q * 1.6) + .15 * ov
            P.update(eyes="wide", mouth="o")
        elif t < 8.9:
            x = SPX; P.update(eyes="squint", mouth="zigzag", look=(.9, .3))
        elif t < 10.0:
            q = ease((t - 8.9) / 1.1); x = SPX - (SPX - 260) * q; y = FEET - 14 * abs(math.sin(t * 11)) * (1 - q)
            P.update(eyes="closed", mouth="frown", look=(-.6, 0))
        elif t < 10.3:
            x = 260; P.update(eyes="normal", mouth="frown", look=(-.6, 0))
        else:
            x = 260; P.update(eyes="wide", mouth="o", look=(.6, .3))
            if t > 10.7: P.update(eyes="normal", mouth="smile")
        # draw spring (behind kiddo when he stands on it)
        sp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); spring_draw(ImageDraw.Draw(sp), sx_, h, tilt)
        if spring_y_off:
            sp2 = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sp2.paste(sp, (0, int(spring_y_off))); sp = sp2
        shadow(img, sx_, -spring_y_off, w=110)
        img.alpha_composite(sp)
        if show and y > -700:
            shadow(img, x, max(0, FEET - y), w=180 * sx)
            kid(img, t, x, y, sx, sy, rot, **P)
        d = ImageDraw.Draw(img)
        if speed:
            for j in range(5):
                xx = x - 160 + j * 80
                d.line([(xx, y + 60), (xx, y + 420)], fill=(255, 255, 255), width=12)
        if 3.25 <= t < 4.6 or 5.05 <= t < 6.0:  # ceiling dust
            t0 = 3.25 if t < 4.6 else 5.05
            for j in range(10):
                u = t - t0 - j * .04
                if u > 0:
                    px = SPX - 140 + j * 30 + 20 * math.sin(j * 3 + u * 4); py = 20 + 900 * u * u + 120 * u
                    if py < FEET: d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(200, 185, 165), outline=(150, 135, 120))
        if dizzy:
            stars_ring(d, x, FEET - 168 * K * sy - 40, t, r=160)
        return shake_img(img, shake, t)
    return frame


# ================================================================== GAG 5: the chair that won't be sat on
SEATH = 245           # seat height above the floor
SEATY = FEET - SEATH  # kiddo's feet y when sitting
CK0, CA, CB, CC = 250, 600, 850, 330
KS = .78  # kiddo a bit smaller here so the chair reads  # kiddo start, chair spots A/B/C
WOOD, WOOD_D, WOOD_L = (196, 128, 70), (150, 92, 50), (222, 160, 100)


def chair_draw(img, x, t, lift=0.0, lean=0.0, eyes="open", look=(0.0, 0.0), run=False, smirk=False):
    d = ImageDraw.Draw(img)
    base = FEET - lift; st = base - SEATH; l = lean * 70
    ph = math.sin(t * 40) if run else 0.0
    for lx, top, dk in ((-105, st + 10, True), (105, st + 10, True), (-130, st + 30, False), (130, st + 30, False)):
        wig = (22 * ph if (lx < 0) == (top > st + 20) else -22 * ph)
        d.line([(x + lx + l * .3, top), (x + lx + wig, base - (14 if dk else 0))], fill=DARK, width=30)
        d.line([(x + lx + l * .3, top), (x + lx + wig, base - (14 if dk else 0))], fill=WOOD_D if dk else WOOD, width=20)
    for px in (-112, 112):  # back posts
        d.line([(x + px, st), (x + px + l, st - 360)], fill=DARK, width=28)
        d.line([(x + px, st), (x + px + l, st - 360)], fill=WOOD_D, width=18)
    d.rounded_rectangle([x - 150 + l, st - 380, x + 150 + l, st - 170], radius=28, fill=WOOD, outline=DARK, width=6)
    d.rounded_rectangle([x - 125 + l, st - 360, x + 125 + l, st - 330], radius=10, fill=WOOD_L)
    # face on the backrest
    ex, ey = x + l, st - 275
    for sgn in (-1, 1):
        cx = ex + sgn * 48
        if eyes == "wink" and sgn < 0 or eyes == "closed":
            d.arc([cx - 26, ey - 14, cx + 26, ey + 22], 200, 340, fill=DARK, width=7)
            continue
        r = 30 if eyes == "wide" else 25
        d.ellipse([cx - r, ey - r, cx + r, ey + r], fill=(255, 255, 255), outline=DARK, width=5)
        pr = 9 if eyes == "wide" else 12
        px_, py_ = cx + look[0] * (r - pr - 3), ey + look[1] * (r - pr - 3)
        d.ellipse([px_ - pr, py_ - pr, px_ + pr, py_ + pr], fill=DARK)
    if smirk:
        d.arc([ex - 40, ey + 20, ex + 50, ey + 70], 10, 160, fill=DARK, width=7)
    # seat
    d.rounded_rectangle([x - 165, st - 32, x + 165, st + 6], radius=12, fill=WOOD_L, outline=DARK, width=5)
    d.rounded_rectangle([x - 170, st, x + 170, st + 38], radius=10, fill=WOOD, outline=DARK, width=5)


def arc_pos(q, x0, y0, x1, y1, hgt):
    return x0 + (x1 - x0) * q, y0 + (y1 - y0) * q - hgt * math.sin(math.pi * q)


def gag_chair(tl):
    T = 12.0
    tl.vocal(.2, "Hup!", 1.35); tl.fx(.62, "whoosh"); tl.fx(.92, "slide_down"); tl.fx(1.05, "bonk")
    tl.vocal(2.2, "La la la...", 1.35)
    tl.fx(3.3, "whoosh"); tl.fx(3.38, "boing"); tl.fx(3.9, "bonk"); tl.fx(3.92, "boing")
    tl.fx(4.05, "pop"); tl.fx(4.2, "pop")
    tl.vocal(4.35, "Grrrr!", 1.1)
    tl.fx(5.0, "creak"); tl.fx(5.35, "whoosh"); tl.fx(5.7, "whoosh")
    tl.vocal(6.15, "Uh oh.", 1.25)
    tl.fx(6.5, "slide_down")
    tl.fx(6.75, "honk"); tl.fx(6.75, "splat"); tl.fx(6.77, "bonk"); tl.fx(6.8, "crash")
    tl.fx(8.0, "pop")
    for k in range(4):
        tl.fx(8.3 + k * .15, "tick")
    tl.fx(8.9, "whoosh"); tl.fx(9.25, "ding"); tl.vocal(9.35, "Ahhh...", 1.2)
    tl.fx(9.95, "boing"); tl.fx(10.0, "whoosh"); tl.vocal(10.05, "Waah!", 1.35)
    tl.fx(10.55, "bonk")
    tl.fx(11.0, "sparkle"); tl.fx(11.02, "ding")
    tl.duration = T
    ANGRY = (235, 50, 45)

    def frame(t):
        img = Image.new("RGBA", (W, H)); background(img, wall=(206, 232, 246), floor=(220, 186, 146))
        d = ImageDraw.Draw(img)
        # a little picture frame on the wall for depth
        d.rounded_rectangle([110, 520, 330, 700], radius=10, fill=(255, 250, 235), outline=DARK, width=6)
        R.paste_emoji(img, "🌈", 220, 612, 120)
        # ------------------------------------------------ chair state
        cx, clift, clean, ceyes, clook, crun, smirk, cspeed = CA, 0.0, 0.0, "open", (-.8, .2), False, False, 0
        if t < .62:
            clook = (-.8, .2) if t < .4 else (-.7, -.3)
        elif t < .8:
            q = ease((t - .62) / .18); cx = CA + (CB - CA) * q; clean = -.6 * math.sin(math.pi * q); crun = True; cspeed = 1
            ceyes = "wide"
        elif t < 2.1:
            cx = CB; clook = (0, -.9) if t > 1.4 else (-.8, 0); clift = 6 * abs(math.sin(t * 5)) if t > 1.4 else 0
        elif t < 3.3:
            cx = CB; ceyes = "closed" if t > 2.5 else "open"; clook = (-.8, 0)
        elif t < 3.38:
            cx = CB; ceyes = "wide"; clook = (-.9, -.3)
        elif t < 3.9:
            q = ease((t - 3.38) / .52); cx, cy_ = arc_pos(q, CB, 0, CC, 0, 900); clift = cy_ * -1 if cy_ < 0 else 0
            clift = 680 * math.sin(math.pi * q); clean = .5 * math.sin(2 * math.pi * q); ceyes = "wide"; crun = True
        elif t < 5.7:
            cx = CC; clook = (.9, 0)
            if 4.0 <= t < 4.35: clift = 40 * abs(math.sin((t - 4.0) * math.pi / .175))
            if t > 5.35: ceyes = "wide"; clook = (.6, -.9)
        elif t < 8.3:
            q = ease_in(seg(t, 5.7, 5.9)); cx = CC - 600 * q; crun = True; cspeed = -1 if t < 5.95 else 0; clean = .6
        elif t < 8.9:
            q = (t - 8.3) / .6; cx = -300 + (CC - 140 + 300) * q; clift = 18 * abs(math.sin(q * 4 * math.pi)); crun = True
            ceyes = "open"; clook = (.9, -.2)
        elif t < 9.95:
            q = ease(seg(t, 8.9, 9.05)); cx = CC - 140 + 140 * q
        elif t < 10.6:
            u = t - 9.95
            if u < .12: clift = 70 * math.sin(math.pi * u / .12); clean = -.8 * math.sin(math.pi * u / .12); cx = CC
            else:
                q = ease((u - .12) / .48); cx = CC + (CA - CC) * q; crun = True; clean = -.5 * math.sin(math.pi * q); cspeed = 1
        else:
            cx = CA; clook = (-.8, .2)
            if 11.0 <= t < 11.6: ceyes = "wink"; smirk = True
        # ------------------------------------------------ kiddo state
        x, y, sx, sy, rot = float(CK0), FEET, 1., 1., 0.
        P = dict(eyes="happy", mouth="smile", look=(0, 0))
        shake = 0; dizzy = False; steam = False; speed_v = False; puffs = None
        if t < .2:
            q = math.sin(math.pi * .5 * (t / .2)); sy = 1 - .15 * q; sx = 1 + .1 * q
        elif t < .8:
            q = ease((t - .2) / .6); x, y = arc_pos(q, CK0, FEET, CA, SEATY, 230)
            P.update(eyes="happy", mouth="open", arms="up"); sy = 1.08; sx = .95
        elif t < .92:
            x, y = CA, SEATY; P.update(eyes="wide", mouth="o", look=(0, .8))
        elif t < 1.05:
            x = CA; y = SEATY + (FEET - SEATY) * ease_in((t - .92) / .13); P.update(eyes="wide", mouth="scream", arms="up")
        elif t < 1.5:
            x = CA; u = t - 1.05; b = math.exp(-u * 7)
            sy = 1 - .45 * b; sx = 1 + .35 * b; shake = 7 * b; P.update(eyes="x", mouth="wavy")
        elif t < 2.1:
            x = CA; P.update(eyes="squint", mouth="zigzag", look=(.8, 0))
        elif t < 3.3:
            q = (t - 2.1) / 1.2; x = CA + 60 * q; y = FEET - 10 * abs(math.sin(t * 8))
            P.update(eyes="closed", mouth="smile", look=(0, .25)); rot = 5 * math.sin(t * 4)
        elif t < 3.75:
            q = ease((t - 3.3) / .45); x, y = arc_pos(q, CA + 60, FEET, CB, SEATY, 190)
            P.update(eyes="wide", mouth="open", arms="up")
        elif t < 3.9:
            x = CB; y = SEATY + (FEET - SEATY) * ease_in((t - 3.75) / .15); P.update(eyes="wide", mouth="scream", arms="up")
        elif t < 4.3:
            x = CB; u = t - 3.9; b = math.exp(-u * 8); sy = 1 - .35 * b; sx = 1 + .3 * b
            P.update(eyes="wide", mouth="o", look=(-.9, 0))
        elif t < 5.0:
            x = CB + 6 * math.sin(t * 70); q = seg(t, 4.3, 4.6)
            P.update(eyes="squint", mouth="zigzag", look=(-.8, 0), body=lerp_col(CORAL, ANGRY, q)); steam = True
            sx = 1 + .05 * q; sy = 1 + .05 * q
        elif t < 5.35:
            x = CB; q = ease((t - 5.0) / .35); sx = 1 + .3 * q; sy = 1 - .38 * q
            P.update(eyes="squint", mouth="zigzag", look=(-.8, 0), body=ANGRY); steam = True
        elif t < 5.85:
            q = ease((t - 5.35) / .5); x = CB + (CC - CB) * q; y = FEET - 520 * math.sin(math.pi * .5 * q)
            sx = .8; sy = 1.3; P.update(eyes="squint", mouth="open", arms="up", body=lerp_col(ANGRY, CORAL, q))
        elif t < 6.55:
            x = CC; y = FEET - 520 + 6 * math.sin((t - 5.85) * 9); sx = 1 - .05 * ease(seg(t, 5.85, 6.0)); sy = 1
            if t < 6.05: P.update(eyes="squint", mouth="open", arms="up")
            elif t < 6.15: P.update(eyes="wide", mouth="o", look=(0, .9), arms="up")
            else: P.update(eyes="normal", mouth="o", look=(0, .25), arms="up")
        elif t < 6.75:
            x = CC; y = FEET - 520 + 460 * ease_in((t - 6.55) / .2); sx = .72; sy = 1.38
            P.update(eyes="wide", mouth="scream", arms="up"); speed_v = True
        elif t < 8.0:
            x = CC; u = t - 6.75; wob = math.sin(u * 18) * math.exp(-u * 2)
            sx = 1.75 + .1 * wob; sy = .22 - .03 * wob; shake = 24 * math.exp(-u * 6); dizzy = u > .25
            P.update(eyes="dizzy", mouth="wavy"); puffs = u
        elif t < 8.35:
            x = CC; q = (t - 8.0) / .35; ov = math.sin(q * math.pi * 2.5) * math.exp(-q * 3)
            sx = 1.75 - .75 * ease(q * 1.6) - .2 * ov; sy = .22 + .78 * ease(q * 1.6) + .15 * ov
            P.update(eyes="wide", mouth="o")
        elif t < 8.9:
            x = CC; P.update(eyes="normal", mouth="frown", look=(0, .25))
        elif t < 9.2:
            x = CC; q = ease(seg(t, 8.9, 9.05)); y = FEET - SEATH * q - 40 * math.sin(math.pi * seg(t, 8.9, 9.2))
            P.update(eyes="wide", mouth="o", arms="up")
        elif t < 9.95:
            x = CC; y = SEATY - 6 * abs(math.sin(t * 9)); P.update(eyes="happy", mouth="smile", arms="down")
            rot = 4 * math.sin(t * 7)
        elif t < 10.55:
            q = ease((t - 9.95) / .6); x, y = arc_pos(q, CC, SEATY, CK0, FEET, 520); rot = -360 * q
            P.update(eyes="x", mouth="scream", arms="up")
        elif t < 11.3:
            u = t - 10.55; b = math.exp(-u * 8); sy = 1 - .3 * b; sx = 1 + .25 * b
            P.update(eyes="normal", mouth="frown", look=(0, .25))
            if t > 11.0: P.update(look=(.8, 0))
        elif t < 11.75:
            P.update(eyes="normal", mouth="frown", look=(0, .25))
        # ------------------------------------------------ draw
        if -250 < cx < W + 250:
            shadow(img, cx, clift, w=150)
            chair_draw(img, cx, t, clift, clean, ceyes, clook, crun, smirk)
        d = ImageDraw.Draw(img)
        if cspeed:
            for j in range(5):
                yy = FEET - 420 + j * 80; x0 = cx - cspeed * 210
                d.line([(x0, yy), (x0 - cspeed * 300, yy)], fill=(255, 255, 255), width=12)
        shadow(img, x, max(0, FEET - y), w=150 * sx)
        kid(img, t, x, y, sx * KS, sy * KS, rot, **P)
        d = ImageDraw.Draw(img)
        if speed_v:
            for j in range(5):
                xx = x - 160 + j * 80
                d.line([(xx, y - 700), (xx, y - 1100)], fill=(255, 255, 255), width=12)
        if steam:
            for j in range(4):
                ph = (t * 2.5 + j / 4) % 1; side = -1 if j % 2 else 1
                px = x + side * (70 + 60 * ph); py = FEET - 168 * K * KS * sy - 30 - 160 * ph; r = 22 + 30 * ph
                d.ellipse([px - r, py - r, px + r, py + r], fill=(235, 235, 240), outline=(170, 170, 185), width=3)
        if puffs is not None and puffs < .7:
            for j in range(8):
                a = math.pi + j * math.pi / 7; dd = 160 + 520 * puffs; r = 34 * (1 - puffs / .7)
                px = x + math.cos(a) * dd * 1.2; py = FEET - 20 + math.sin(a) * dd * .35
                d.ellipse([px - r, py - r, px + r, py + r], fill=(235, 220, 200), outline=(170, 150, 130), width=3)
        if dizzy:
            stars_ring(d, x, FEET - 168 * K * KS * sy - 40, t, r=170)
        return shake_img(img, shake, t)
    return frame


GAGS = {"door": gag_door, "sneeze": gag_sneeze, "bubble": gag_bubble, "spring": gag_spring, "chair": gag_chair}


def main(ep_path, preview=None):
    ep = json.load(open(ep_path))
    out = os.path.join(ROOT, "out", ep["id"]); os.makedirs(out, exist_ok=True)
    tl = GTL(ep)
    frame = GAGS[ep["gag"]](tl)

    def cap(img, t):
        if ep.get("hook"):
            d = ImageDraw.Draw(img)
            R.big_text(d, (W / 2, 330), ep["hook"], R.fit_size(ep["hook"], 104, 980), 1 + .03 * math.sin(t * 4), (40, 40, 60), 12)
        return img
    print(f"{ep['id']}: {ep['gag']} {tl.duration:.1f}s")
    if preview:
        sheet = Image.new("RGB", (240 * len(preview), 427))
        for k, ts_ in enumerate(preview):
            sheet.paste(cap(frame(ts_), ts_).convert("RGB").resize((240, 427)), (240 * k, 0))
        sheet.save(os.path.join(out, "preview.png")); print("preview:", os.path.join(out, "preview.png"))
        return
    apath = os.path.join(out, "audio.wav"); D.mix(tl, apath)
    vpath = os.path.join(out, "video.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-i", apath, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                             vpath], stdin=subprocess.PIPE)
    for fi in range(int(tl.duration * FPS)):
        proc.stdin.write(cap(frame(fi / FPS), fi / FPS).convert("RGB").tobytes())
    proc.stdin.close(); proc.wait(); os.remove(apath)
    cap(frame(ep.get("thumb_t", 0.5)), 0).convert("RGB").save(os.path.join(out, "thumbnail.png"))
    D.srt(tl, os.path.join(out, "subtitles.srt"))
    json.dump(dict(ep["seo"], duration=round(tl.duration, 1)), open(os.path.join(out, "upload.json"), "w"), indent=2,
              ensure_ascii=False)
    print("done:", vpath, f"{tl.duration:.1f}s", "ffmpeg rc", proc.returncode)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) > 1 and a[1] == "--preview":
        main(a[0], [float(x) for x in a[2:]])
    else:
        main(a[0])
