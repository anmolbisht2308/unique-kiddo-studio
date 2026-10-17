"""Pick a Door with Kiddo: comedy door-choice Shorts.

Usage:  python3 engine/doors.py episodes/door01_x.json [--preview t1 t2 ...]
Episode schema: see README.md ("doors" format).
"""
import json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import render as R  # noqa: E402  (helpers: font, pop, big_text, letter_word, paste_emoji, emoji_img, tone, resample)
import sfx  # noqa: E402
import tts  # noqa: E402
from kiddo_fx import kiddo_layer, place_kiddo, lerp_col, CORAL  # noqa: E402
from kiddo import star_pts  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 44100
DARK = (55, 45, 70)
DOOR_X = [200, 540, 880]
DOOR_W, DOOR_TOP, DOOR_BOT = 270, 470, 1060
FLOOR_Y = 1090
KID_X, KID_Y, KID_S = 540, 1735, 230
ITEM_POS = (540, 850, 380)
NUM = ["one", "two", "three"]
DOOR_COLS = [(240, 96, 86), (78, 140, 232), (84, 186, 110)]
clamp = R.clamp


def ease(x):
    x = clamp(x); return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ reactions
REACT_SFX = {
    "sour": [(0, "boing")], "hot": [(0, "slide_up"), (.3, "sizzle")], "win": [(0, "fanfare"), (.15, "sparkle")],
    "love": [(0, "sparkle")], "stinky": [(0, "pfft")], "cold": [(0, "brrr")], "wet": [(0, "splash"), (.5, "splash")],
    "slip": [(0, "slide_down"), (.85, "bonk")], "tickle": [(0, "boing")], "scared": [(0, "roar")],
    "bounce": [(0, "boing"), (.55, "boing"), (1.1, "boing")], "sneeze": [(1.0, "whoosh")], "float": [(0, "float_up")],
    "buzz": [(0, "buzz")],
}
WRONG_COL = (240, 90, 60)
FACES = {"sour": "😖", "hot": "🥵", "stinky": "🤢", "cold": "🥶", "wet": "😩", "slip": "😵", "tickle": "🤣",
         "scared": "😱", "buzz": "😨", "bounce": "😳", "sneeze": "🤧", "float": "🤩", "win": "🥳", "love": "😍"}


def place_face(img, ch, P, size=360):
    """emoji-face host (for the family edition, no Kiddo)"""
    e = R.emoji_img(ch, size)
    nw, nh = max(2, int(e.width * P["sx"])), max(2, int(e.height * P["sy"]))
    L = e.resize((nw, nh), Image.BICUBIC)
    if abs(P["rot"]) > .2:
        L = L.rotate(P["rot"], resample=Image.BICUBIC, expand=True)
    x = KID_X + P["dx"]; y = KID_Y + P["dy"] * .6 + 15
    img.alpha_composite(L, (int(x - L.width / 2), int(y - nh / 2 - L.height / 2)))


def kid_pose(kind, u, t):
    P = dict(eyes="normal", mouth="smile", arms="down", body=CORAL, sx=1., sy=1., rot=0., dx=0., dy=0.,
             shake=0., cheeks=1., look=(0., -.5))
    r = ease(u / .3)
    if kind == "sour":
        w = math.sin(u * 22) * math.exp(-u * .7)
        P.update(eyes="squint", mouth="pucker", body=lerp_col(CORAL, (210, 205, 70), r * .85),
                 sx=1 - .12 * r + .06 * w, sy=1 + .08 * r - .06 * w, rot=7 * math.sin(u * 17) * math.exp(-u * .6))
    elif kind == "hot":
        P.update(eyes="wide", mouth="scream", arms="up", cheeks=1.7,
                 body=lerp_col(CORAL, (232, 36, 28), clamp(u / .8)),
                 dx=9 * math.sin(u * 40) * r, dy=-abs(math.sin(u * 8)) * 55 * r, shake=7 * r * math.exp(-u * .5))
    elif kind == "win":
        j = abs(math.sin(u * 6.5))
        P.update(eyes="star" if int(u * 2.5) % 2 else "happy", mouth="open", arms="up",
                 dy=-85 * j, sy=.88 + .2 * j, sx=1.1 - .16 * j)
    elif kind == "love":
        P.update(eyes="heart", mouth="open", body=lerp_col(CORAL, (255, 120, 160), .35 * r),
                 rot=6 * math.sin(u * 3), dy=-12 * abs(math.sin(u * 3)))
    elif kind == "stinky":
        P.update(eyes="x", mouth="wavy", body=lerp_col(CORAL, (150, 190, 90), .75 * r), arms="cover",
                 rot=8 * math.sin(u * 4) * r, sy=1 - .05 * r)
    elif kind == "cold":
        P.update(eyes="wide", mouth="zigzag", arms="cover", body=lerp_col(CORAL, (120, 180, 240), .8 * r),
                 dx=5 * math.sin(u * 70) * r, sx=1 - .08 * r)
    elif kind == "wet":
        P.update(eyes="closed", mouth="frown", body=lerp_col(CORAL, (205, 95, 105), .5 * r),
                 sy=1 - .1 * r, sx=1 + .08 * r)
    elif kind == "slip":
        if u < .9:
            q = u / .9
            P.update(eyes="wide", mouth="scream", arms="up", rot=-360 * ease(q), dy=-280 * math.sin(math.pi * q))
        else:
            b = math.exp(-(u - .9) * 6) * math.sin((u - .9) * 25)
            P.update(eyes="dizzy", mouth="wavy", sy=1 - .2 * b, sx=1 + .15 * b)
    elif kind == "tickle":
        P.update(eyes="happy", mouth="open", arms="up", rot=11 * math.sin(u * 19) * r,
                 sx=1 + .05 * math.sin(u * 23), sy=1 - .05 * math.sin(u * 23))
    elif kind == "scared":
        jb = math.exp(-u * 5) * math.sin(min(u, .4) / .4 * math.pi) if u < .4 else 0
        P.update(eyes="wide", mouth="scream", arms="cover", body=lerp_col(CORAL, (255, 175, 165), .5 * r),
                 dy=-90 * jb, dx=6 * math.sin(u * 55) * r)
    elif kind == "buzz":
        P.update(eyes="wide", mouth="o", look=(math.sin(u * 7), -.4), dx=60 * math.sin(u * 4) * r,
                 rot=-8 * math.cos(u * 4) * r)
    elif kind == "bounce":
        ph = (u % .55) / .55
        hit = math.exp(-ph * 9)
        P.update(eyes="wide", mouth="o", look=(0, -1), sy=1 - .14 * hit, sx=1 + .1 * hit)
    elif kind == "sneeze":
        if u < 1.0:
            P.update(eyes="closed", mouth="o", sx=1 + .15 * u, sy=1 + .12 * u, dy=-10 * u)
        else:
            v = u - 1.0; k = math.exp(-v * 3)
            P.update(eyes="squint", mouth="open", rot=-16 * k, dx=-70 * k)
    elif kind == "float":
        f = math.sin(math.pi * clamp(u / 3.2))
        P.update(eyes="happy", mouth="open", arms="up", dy=-330 * f, rot=6 * math.sin(u * 3))
    return P


def kid_top(P):
    return KID_Y + P["dy"] - 168 * KID_S / 100 * P["sy"]


def item_target(kind, u, P):
    """where the revealed item sits during the reaction: (x, y, size)"""
    kx = KID_X + P["dx"]; top = kid_top(P)
    if kind == "bounce":
        ph = (u % .55) / .55
        return kx, top - 70 - 150 * math.sin(math.pi * ph), 190
    if kind == "wet":
        return kx, top - 170, 260
    if kind == "float":
        return kx, top - 260, 240
    if kind == "tickle":
        return kx + 250 + 15 * math.sin(u * 12), KID_Y - 230 + 30 * math.sin(u * 9), 200
    if kind == "buzz":
        return kx + 230 * math.cos(u * 4), top - 40 + 70 * math.sin(u * 8), 150
    if kind == "scared":
        x, y, s = ITEM_POS; return x, y, s * (1 + .08 * math.sin(u * 30) * math.exp(-u))
    x, y, s = ITEM_POS
    return x, y + 10 * math.sin(u * 3), s


def draw_fx(kind, u, img, ov, P, seed):
    """effects drawn on the alpha overlay `ov` (and emojis on img). u = time since reaction."""
    d = ImageDraw.Draw(ov)
    kx = KID_X + P["dx"]; top = kid_top(P)
    rnd = random.Random(seed)
    if kind == "hot":
        for j in range(7):
            ph = (u * 1.3 + j / 7) % 1
            x = kx + (-1 if j % 2 else 1) * (40 + 25 * j % 70) + 20 * math.sin(ph * 6 + j)
            y = top + 30 - ph * 300; rr = 22 + 55 * ph
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 255, 255, int(200 * (1 - ph))))
        for j in range(4):
            ph = (u * 1.6 + j / 4) % 1
            ang = j * 1.57 + .8
            R.paste_emoji(img, "🔥", kx + math.cos(ang) * (170 + 60 * ph), KID_Y - 200 + math.sin(ang) * 120 - 80 * ph,
                          90 * (1 - ph * .5))
    elif kind == "sour":
        for j in range(6):
            a = j * 1.05 + u * 2
            on = (int(u * 8) + j) % 2
            if on:
                r0, r1 = 200, 250
                cx, cy = kx, KID_Y - 200
                d.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0 * .8),
                        (cx + math.cos(a) * r1, cy + math.sin(a) * r1 * .8)], fill=(240, 200, 40, 255), width=10)
    elif kind in ("win",):
        for j in range(110):
            x0 = rnd.uniform(0, W); vx = rnd.uniform(-60, 60); st = rnd.uniform(0, 1.2)
            if u < st: continue
            tt = u - st; y = -40 + tt * rnd.uniform(380, 620); x = x0 + vx * tt + 30 * math.sin(tt * 4 + j)
            if y > H + 40: continue
            c = R.RAINBOW[j % 6]; a = tt * rnd.uniform(4, 9) + j; s = rnd.uniform(10, 18)
            pts = [(x + math.cos(a + q) * s * (1.6 if q in (0, math.pi) else .7),
                    y + math.sin(a + q) * s * (1.6 if q in (0, math.pi) else .7)) for q in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
            d.polygon(pts, fill=c + (255,))
    elif kind == "love":
        for j in range(6):
            ph = (u * .7 + j / 6) % 1
            x = kx + (j - 2.5) * 70 + 30 * math.sin(ph * 8 + j)
            R.paste_emoji(img, "❤️", x, top - ph * 380, 80 * (1 - ph * .4))
    elif kind == "stinky":
        for j in range(3):
            pts = []
            for q in range(30):
                v = q / 29
                x = ITEM_POS[0] + (kx - ITEM_POS[0]) * v + (j - 1) * 70
                y = ITEM_POS[1] + 150 + (KID_Y - 260 - ITEM_POS[1] - 150) * v + 22 * math.sin(v * 12 - u * 8 + j)
                pts.append((x, y))
            d.line(pts, fill=(120, 190, 60, 200), width=12, joint="curve")
        R.paste_emoji(img, "🪰", kx + 190 * math.cos(u * 5), top - 10 + 60 * math.sin(u * 10), 90)
    elif kind == "cold":
        for j in range(18):
            x = rnd.uniform(40, W - 40); sp = rnd.uniform(160, 300)
            y = (rnd.uniform(0, H) + u * sp) % (H + 100) - 50
            R.paste_emoji(img, "❄️", x + 20 * math.sin(u * 2 + j), y, rnd.uniform(50, 85))
    elif kind == "wet":
        cx, cy, _ = item_target("wet", u, P)
        for j in range(16):
            ph = (u * 1.8 + j / 16) % 1
            x = cx - 110 + (j * 37) % 220; y = cy + 60 + ph * (KID_Y - cy - 60)
            d.ellipse([x - 9, y - 16, x + 9, y + 16], fill=(80, 160, 240, 230))
        pw = 140 + 60 * clamp(u / 1.5)
        d.ellipse([kx - pw, KID_Y - 18, kx + pw, KID_Y + 22], fill=(110, 180, 245, 170))
    elif kind == "slip" and u > .9:
        for j in range(3):
            a = u * 5 + j * 2.09
            x, y = kx + math.cos(a) * 120, top - 30 + math.sin(a) * 35
            d.polygon(star_pts(x, y, 30, u * 200), fill=(255, 205, 45, 255), outline=DARK + (255,))
    elif kind == "tickle":
        for j in range(3):
            ph = (u * .9 + j / 3) % 1
            x = kx + (-200 + j * 200); y = top - 40 - ph * 220
            d.text((x, y), "hee!", font=R.font(70), fill=(240, 80, 140, int(255 * (1 - ph))), anchor="mm",
                   stroke_width=6, stroke_fill=(255, 255, 255, int(255 * (1 - ph))))
    elif kind == "scared":
        for j in range(8):
            a = j * .785
            on = (int(u * 10) + j) % 2
            if on:
                cx, cy = kx, KID_Y - 200
                d.line([(cx + math.cos(a) * 210, cy + math.sin(a) * 190), (cx + math.cos(a) * 260, cy + math.sin(a) * 235)],
                       fill=DARK + (255,), width=9)
    elif kind == "sneeze" and u > 1.0:
        v = u - 1.0
        for j in range(5):
            y = KID_Y - 300 + j * 50
            x0 = kx - 200 - v * 500; x1 = x0 - 160
            d.line([(x0, y), (x1, y)], fill=(255, 255, 255, int(255 * math.exp(-v * 1.5))), width=12)
    elif kind == "float":
        cx, cy, s = item_target("float", u, P)
        d.line([(cx, cy + s * .45), (kx + 50, top + 40)], fill=DARK + (255,), width=5)


# ------------------------------------------------------------------ timeline
class TL:
    def __init__(self, ep):
        self.ep = ep
        self.nar = tts.voice(ep.get("voice", {"af_heart": 1.0}))
        self.kid = tts.voice(ep.get("kiddo_voice", {"af_bella": 1.0}))
        self.clips, self.sfx, self.subs, self.segs = [], [], [], []

    def say(self, t, text, who="nar"):
        if who == "kid":
            a, sr = tts.tts(text, self.kid, self.ep.get("kiddo_speed", 1.0))
            x = R.resample(a.astype(float), sr * self.ep.get("kiddo_pitch", 1.16))
        else:
            a, sr = tts.tts(text, self.nar, self.ep.get("speed", 0.98))
            x = R.resample(a.astype(float), sr)
        nz = np.where(np.abs(x) > .01)[0]
        if len(nz): x = x[max(0, nz[0] - 600): nz[-1] + 1200]
        self.clips.append((t, x, who))
        end = t + len(x) / SR
        self.subs.append((t, end, text))
        return end


def build(ep):
    tl = TL(ep)
    doors = ep["doors"]
    e = tl.say(.25, ep.get("hook_line", "Don't pick the wrong door!"))
    e = tl.say(e + .1, ep.get("ask_line", "Which door will you choose?"))
    tl.hl = []
    t = e + .25
    for j in range(3):
        tl.sfx.append((t, "pop")); tl.hl.append(t)
        t = max(t + .7, tl.say(t, NUM[j].capitalize() + ("?" if j == 2 else "...")) + .1)
    tl.cd = t + .15
    for j in range(3):
        tl.sfx.append((tl.cd + j, "tick"))
    t = tl.cd + 3.0
    tl.sfx.append((t, "ding"))
    tl.hook_end = t
    t += .25
    order = ep.get("open_order", [0, 1, 2])
    for idx in order:
        dr = doors[idx]; win = dr.get("win", False)
        g = dict(idx=idx, start=t, door=dr, win=win, kind=dr["reaction"])
        tl.say(t, f"Door number {NUM[idx]}!")
        tl.sfx.append((t + .15, "drumroll_long" if win else "drumroll"))
        g["open"] = t + .15 + (1.7 if win else 1.1)
        tl.sfx += [(g["open"], "creak"), (g["open"] + .05, "pop")]
        g["react"] = g["open"] + .4
        for off, name in REACT_SFX.get(g["kind"], []):
            tl.sfx.append((g["react"] + off, name))
        e = tl.say(g["react"] + .2, dr["kiddo_line"], "kid")
        if g["kind"] == "sneeze":
            e = max(e, g["react"] + 1.3)
        g["line_t"] = e + .2
        e = tl.say(g["line_t"], dr["line"])
        if win:
            g["end"] = e + .7
        else:
            tl.sfx.append((e + .05, "trombone"))
            g["end"] = e + 1.35
        tl.segs.append(g); t = g["end"]
    tl.outro = t
    e = tl.say(t + .1, ep.get("outro_line", "Which door did you pick? Let's play again!"))
    tl.duration = e + 1.0
    return tl


# ------------------------------------------------------------------ drawing
def scene_bg(img, ep, t):
    d = ImageDraw.Draw(img)
    wall = tuple(ep.get("wall", (255, 234, 205)))
    stripe = tuple(min(255, c + 12) for c in wall)
    d.rectangle([0, 0, W, FLOOR_Y], fill=wall)
    for x in range(0, W, 120):
        d.rectangle([x, 0, x + 60, FLOOR_Y], fill=stripe)
    band = tuple(max(0, c - 22) for c in wall)
    d.rectangle([0, FLOOR_Y - 95, W, FLOOR_Y], fill=band)
    d.rectangle([0, FLOOR_Y - 101, W, FLOOR_Y - 92], fill=tuple(max(0, c - 45) for c in wall))
    floor = (226, 180, 128)
    d.rectangle([0, FLOOR_Y, W, H], fill=floor)
    for k, y in enumerate([FLOOR_Y + 60, FLOOR_Y + 150, FLOOR_Y + 270, FLOOR_Y + 420, FLOOR_Y + 610]):
        d.line([(0, y), (W, y)], fill=(200, 152, 102), width=5)
    for k in range(-6, 7):
        d.line([(W / 2 + k * 90, FLOOR_Y), (W / 2 + k * 260, H)], fill=(205, 160, 110), width=4)
    d.rectangle([0, FLOOR_Y - 6, W, FLOOR_Y + 6], fill=(170, 120, 80))
    # rug under Kiddo
    d.ellipse([KID_X - 330, KID_Y - 60, KID_X + 330, KID_Y + 70], fill=tuple(ep.get("rug", (120, 200, 210))))
    d.ellipse([KID_X - 290, KID_Y - 42, KID_X + 290, KID_Y + 52], fill=tuple(min(255, c + 30) for c in ep.get("rug", (120, 200, 210))))


def draw_door(img, ov, j, openp, wobble, hl, col, win_glow, t):
    d = ImageDraw.Draw(img)
    x = DOOR_X[j] + wobble; x0, x1 = x - DOOR_W / 2, x + DOOR_W / 2
    sc = 1 + .08 * hl
    top = DOOR_BOT - (DOOR_BOT - DOOR_TOP) * sc
    # frame + shadow
    d.rounded_rectangle([x0 - 22, top - 22, x1 + 22, DOOR_BOT + 4], radius=18, fill=(150, 96, 60))
    d.rounded_rectangle([x0 - 12, top - 12, x1 + 12, DOOR_BOT], radius=12, fill=(190, 128, 82))
    # inside of the room behind the door
    d.rectangle([x0, top, x1, DOOR_BOT], fill=(58, 40, 88))
    if openp > 0:
        od = ImageDraw.Draw(ov)
        g = (255, 214, 90) if win_glow else (255, 225, 160)
        for r_, a in ((150, 35), (110, 45), (70, 60)):
            od.ellipse([x - r_, (top + DOOR_BOT) / 2 - r_ * 1.3, x + r_, (top + DOOR_BOT) / 2 + r_ * 1.3],
                       fill=g + (int(a * openp),))
        if win_glow:
            for q in range(10):
                a = t * .8 + q * .628
                cx, cy = x, (top + DOOR_BOT) / 2
                od.polygon([(cx, cy), (cx + math.cos(a) * 220, cy + math.sin(a) * 300),
                            (cx + math.cos(a + .2) * 220, cy + math.sin(a + .2) * 300)], fill=(255, 230, 120, 60))
    # panel (hinged on the left)
    th = math.radians(82 * ease(openp))
    fx = x0 + DOOR_W * math.cos(th)
    grow = 1 + .16 * math.sin(th)
    ph = DOOR_BOT - top
    pts = [(x0, top), (fx, top - ph * (grow - 1) / 2), (fx, DOOR_BOT + ph * (grow - 1) / 2 * .2), (x0, DOOR_BOT)]
    shade = 1 - .35 * math.sin(th)
    pc = tuple(int(c * shade) for c in col)
    d.polygon(pts, fill=pc, outline=DARK)
    if openp < .35:
        lc = tuple(min(255, int(c * 1.15)) for c in col)
        m = 26
        for (py0, py1) in ((top + m, top + ph * .45), (top + ph * .52, DOOR_BOT - m)):
            d.rounded_rectangle([x0 + m, py0, x1 - m, py1], radius=14, fill=lc)
        d.ellipse([x1 - 50, top + ph * .5 - 16, x1 - 18, top + ph * .5 + 16], fill=(255, 205, 45), outline=DARK, width=3)
        d.text((x, top + ph * .45), "?", font=R.font(170), fill=(255, 255, 255), anchor="mm", stroke_width=8,
               stroke_fill=DARK)
    # number plaque
    pr = 48 * (1 + .25 * hl)
    py = top - 70
    d.ellipse([x - pr, py - pr, x + pr, py + pr], fill=(255, 205, 45) if hl > .05 else (255, 255, 255), outline=DARK, width=6)
    d.text((x, py), str(j + 1), font=R.font(int(64 * (1 + .25 * hl))), fill=DARK, anchor="mm")


def frame(tl, t):
    ep = tl.ep
    img = Image.new("RGBA", (W, H))
    scene_bg(img, ep, t)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cols = [tuple(c) for c in ep.get("door_colors", DOOR_COLS)]
    seg = None
    for g in tl.segs:
        if g["start"] <= t < g["end"]: seg = g
    # door states
    items_after = []
    for j in range(3):
        g = next((s for s in tl.segs if s["idx"] == j), None)
        openp = clamp((t - g["open"]) / .45) if g else 0
        hl = 0.0
        for k, th in enumerate(tl.hl):
            if k == j and th <= t < th + .6: hl = math.sin(math.pi * (t - th) / .6)
        wob = 0.0
        if g and g["start"] <= t < g["open"]:
            hl = max(hl, .5 + .5 * math.sin((t - g["start"]) * 10))
            wob = 5 * math.sin(t * 45) * clamp((t - g["start"]) / (g["open"] - g["start"]))
        if tl.cd <= t < tl.hook_end:
            wob = 3 * math.sin(t * 8 + j * 2)
        draw_door(img, ov, j, openp, wob, hl, cols[j], g is not None and g["win"] and openp > 0, t)
        if g and t >= g["open"]:
            items_after.append(g)
    img.alpha_composite(ov); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # title (always on: it is the hook)
    tp = 1 + .03 * math.sin(t * 3)
    t1, t2 = ep.get("title_screen", ["DON'T PICK THE", "WRONG DOOR!"])
    R.letter_word(img, t1, W / 2, 135, int(R.fit_size(t1, 92, 960) * tp), seed=3)
    R.letter_word(img, t2, W / 2, 262, int(R.fit_size(t2, 112, 960) * tp), seed=8)
    # kiddo pose
    P = kid_pose("none", 0, t)
    if t < tl.hook_end:
        if t >= tl.cd:
            P.update(eyes="normal", mouth="o", look=(math.sin(t * 2.5), -.6))
        else:
            hl_j = next((k for k, th in enumerate(tl.hl) if th <= t < th + .7), None)
            if hl_j is not None:
                P.update(look=((DOOR_X[hl_j] - 540) / 340, -.8), mouth="open")
            else:
                P.update(arms="wave", mouth="open" if int(t * 6) % 2 else "smile")
    elif seg is not None and t < seg["react"]:
        P.update(eyes="wide", mouth="o", arms="cover", look=((DOOR_X[seg["idx"]] - 540) / 340, -.9),
                 dx=2 * math.sin(t * 50))
    elif seg is not None:
        P = kid_pose(seg["kind"], t - seg["react"], t)
    elif t >= tl.outro:
        P.update(arms="wave", eyes="happy", mouth="open")
    # revealed items (resting in their doorways, or flying out for the active one)
    for g in items_after:
        dr = g["door"]
        home = (DOOR_X[g["idx"]], (DOOR_TOP + DOOR_BOT) / 2 + 30, 200)
        if seg is g:
            u = t - g["react"]
            tgt = item_target(g["kind"], max(0, u), P)
            if t < g["react"]:
                q = ease((t - g["open"]) / .4)
                cur = tuple(home[k] + (tgt[k] - home[k]) * q for k in range(3))
            elif t > g["end"] - .35:
                q = ease((t - (g["end"] - .35)) / .35)
                cur = tuple(tgt[k] + (home[k] - tgt[k]) * q for k in range(3))
            else:
                cur = tgt
            pop_ = R.pop(t, g["open"], .45)
            if g["win"] and t >= g["react"]:
                od = ImageDraw.Draw(ov)
                for q in range(12):
                    a = t * 1.2 + q * .5236
                    od.polygon([(cur[0], cur[1]), (cur[0] + math.cos(a) * 420, cur[1] + math.sin(a) * 420),
                                (cur[0] + math.cos(a + .18) * 420, cur[1] + math.sin(a + .18) * 420)],
                               fill=(255, 225, 90, 90))
                img.alpha_composite(ov); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            R.paste_emoji(img, dr["emoji"], cur[0], cur[1], cur[2] * max(.05, pop_))
            if g["react"] <= t < g["end"] - .35 and g["kind"] not in ("bounce", "wet", "float", "tickle", "buzz"):
                name = dr["name"].upper()
                f = R.font(64); w_ = f.getlength(name) + 60
                d = ImageDraw.Draw(img)
                y = cur[1] + cur[2] / 2 + 30
                d.rounded_rectangle([cur[0] - w_ / 2, y - 42, cur[0] + w_ / 2, y + 42], radius=42, fill=(255, 255, 255),
                                    outline=DARK, width=5)
                d.text((cur[0], y), name, font=f, fill=DARK, anchor="mm")
        else:
            R.paste_emoji(img, dr["emoji"], *home)
    # kiddo + effects
    if seg is not None and t >= seg["react"]:
        draw_fx(seg["kind"], t - seg["react"], img, ov, P, seed=seg["idx"] * 7 + 1)
    if ep.get("host") == "emoji":
        if t >= tl.outro: face = ep.get("outro_face", "😎")
        elif seg is not None and t >= seg["react"]: face = seg["door"].get("face", FACES.get(seg["kind"], "😮"))
        elif seg is not None: face = "😬"
        elif t >= tl.cd: face = "🤔"
        else: face = "😀"
        place_face(img, face, P)
    else:
        layer = kiddo_layer(KID_S, t, eyes=P["eyes"], mouth=P["mouth"], arms=P["arms"], body=P["body"],
                            look=P["look"], cheeks=P["cheeks"])
        place_kiddo(img, layer, KID_X + P["dx"], KID_Y + P["dy"], P["sx"], P["sy"], P["rot"])
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    # countdown
    if tl.cd <= t < tl.hook_end:
        tt = t - tl.cd; n = 3 - int(tt)
        cx, cy, Rr = W / 2, 1215, 100
        d.ellipse([cx - Rr, cy - Rr, cx + Rr, cy + Rr], fill=(255, 255, 255), outline=DARK, width=7)
        d.pieslice([cx - Rr + 14, cy - Rr + 14, cx + Rr - 14, cy + Rr - 14], -90 + 360 * (tt / 3), 270, fill=(255, 205, 45))
        R.big_text(d, (cx, cy), str(n), 120, R.pop(tt, int(tt), .25), WRONG_COL, 8)
        R.big_text(d, (cx, cy - 165), "PICK ONE!", 84, 1 + .06 * math.sin(t * 8), (60, 120, 230), 9)
    # caption
    if seg is not None and seg["react"] + .1 <= t < seg["end"] - .2:
        u = t - seg["react"] - .1
        cap = seg["door"].get("caption", "")
        if seg["win"]:
            R.letter_word(img, cap or "YOU WIN!", W / 2, 1225, int(130 * min(1.0, R.pop(u, 0, .45)) + 1), seed=5)
        elif t >= seg["line_t"] and ep.get("wrong_text", "WRONG DOOR!"):
            v = t - seg["line_t"]
            R.big_text(d, (W / 2, 1225), ep.get("wrong_text", "WRONG DOOR!"), R.fit_size(ep.get("wrong_text", "WRONG DOOR!"), 112, 1000), R.pop(v, 0, .35) * (1 + .04 * math.sin(v * 10)),
                       (230, 50, 50), 10)
        elif cap:
            sc = R.pop(u, 0, .4) * (1 + .05 * math.sin(u * 12))
            R.big_text(d, (W / 2, 1225), cap, R.fit_size(cap, 120, 1000), sc, tuple(seg["door"].get("caption_color", WRONG_COL)), 10)
    if t >= tl.outro:
        u = t - tl.outro
        R.big_text(d, (W / 2, 1225), ep.get("outro_screen", "PLAY AGAIN!"), R.fit_size(ep.get("outro_screen", "PLAY AGAIN!"), 110, 980), R.pop(u, 0, .45), (60, 120, 230), 10)
    # screen shake
    if P["shake"] > .5:
        sx_ = int(P["shake"] * math.sin(t * 61)); sy_ = int(P["shake"] * math.cos(t * 53))
        base = Image.new("RGBA", (W, H), (255, 234, 205, 255))
        base.paste(img, (sx_, sy_))
        img = base
    return img


# ------------------------------------------------------------------ audio
def mix(tl, path):
    N = int(SR * tl.duration) + SR
    voice = np.zeros(N)
    for st, x, who in tl.clips:
        a = int(st * SR); voice[a:a + len(x)] += x * (1.0 if who == "nar" else 1.05)
    voice /= max(1e-9, np.abs(voice).max()) / .9
    music = np.zeros(N); fx = np.zeros(N)

    def add(buf, sig, at):
        a = int(at * SR); n = min(len(sig), len(buf) - a)
        if n > 0: buf[a:a + n] += sig[:n]
    # bouncy original loop: oom-pah bass + plucky arpeggio + soft shaker
    bpm = 118; beat = 60 / bpm
    prog = [[261.6, 329.6, 392.0], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6], [196.0, 246.9, 293.7]]
    mel = [0, 2, 1, 2, 0, 1, 2, 1]
    tp, n = 0.0, 0
    while tp < tl.duration:
        ch = prog[(n // 8) % 4]
        if n % 2 == 0:
            add(music, R.tone(ch[0] / 2 if n % 4 == 0 else ch[2] / 2, .35, decay=9, vol=.16, harm=(1, .5, .2)), tp)
        add(music, R.tone(ch[mel[n % 8]] * 2, .22, decay=14, vol=.07), tp)
        sh = np.random.default_rng(n).uniform(-1, 1, int(SR * .04)) * np.exp(-np.arange(int(SR * .04)) / 300) * .025
        add(music, sh, tp + beat / 4)
        tp += beat / 2; n += 1
    music /= max(1e-9, np.abs(music).max())
    for at, name in tl.sfx:
        add(fx, sfx.get(name), at)
    # quiet the music during drumrolls so the build-up lands
    duck = np.ones(N)
    for at, name in tl.sfx:
        if name.startswith("drumroll"):
            a = int(at * SR); b = int((at + (1.7 if name.endswith("long") else 1.1)) * SR)
            duck[a:b] = .35
    duck = np.convolve(duck, np.ones(2000) / 2000, mode="same")
    env = np.convolve((np.abs(voice) > .02).astype(float), np.ones(int(SR * .25)) / (SR * .25), mode="same")
    out = music * duck * (.42 - .26 * np.clip(env * 3, 0, 1)) + voice + fx * .8
    out = out[:int(SR * tl.duration)]
    fade = int(SR * .6); out[-fade:] *= np.linspace(1, 0, fade)
    out /= np.abs(out).max() / .92
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def thumbnail(tl, path):
    """first frame of the hook, with Kiddo nervous and door 1 slightly open"""
    img = frame(tl, tl.cd + .4)
    img.convert("RGB").save(path)


def srt(tl, path):
    def ts(x): return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(x % 1 * 1000):03d}"
    with open(path, "w") as f:
        for k, (a, b, text) in enumerate(tl.subs, 1):
            f.write(f"{k}\n{ts(a)} --> {ts(b)}\n{text}\n\n")


def main(ep_path, preview=None):
    ep = json.load(open(ep_path))
    for dr in ep["doors"]:
        R.emoji_path(dr["emoji"])
    out = os.path.join(ROOT, "out", ep["id"]); os.makedirs(out, exist_ok=True)
    tl = build(ep)
    print(f"{ep['id']}: length {tl.duration:.1f}s  hook_end {tl.hook_end:.1f}")
    for g in tl.segs:
        print(f"  door {g['idx'] + 1}: {g['start']:.1f}-{g['end']:.1f} open {g['open']:.1f} react {g['react']:.1f} {g['kind']}")
    if preview:
        sheet = Image.new("RGB", (300 * len(preview), 533))
        for k, ts_ in enumerate(preview):
            sheet.paste(frame(tl, ts_).convert("RGB").resize((300, 533)), (300 * k, 0))
        sheet.save(os.path.join(out, "preview.png")); print("preview:", os.path.join(out, "preview.png"))
        return
    apath = os.path.join(out, "audio.wav"); mix(tl, apath)
    vpath = os.path.join(out, "video.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-i", apath, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                             vpath], stdin=subprocess.PIPE)
    for fi in range(int(tl.duration * FPS)):
        proc.stdin.write(frame(tl, fi / FPS).convert("RGB").tobytes())
    proc.stdin.close(); proc.wait(); os.remove(apath)
    thumbnail(tl, os.path.join(out, "thumbnail.png"))
    srt(tl, os.path.join(out, "subtitles.srt"))
    with open(os.path.join(out, "script.md"), "w") as f:
        f.write(f"# {ep['seo']['title']}\n\n| Time | Line |\n|---|---|\n")
        for a, _, text in tl.subs:
            f.write(f"| {int(a // 60)}:{int(a % 60):02d} | {text} |\n")
    json.dump(dict(ep["seo"], duration=round(tl.duration, 1)), open(os.path.join(out, "upload.json"), "w"), indent=2,
              ensure_ascii=False)
    print("done:", vpath, f"{tl.duration:.1f}s", "ffmpeg rc", proc.returncode)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) > 1 and a[1] == "--preview":
        main(a[0], [float(x) for x in a[2:]])
    else:
        main(a[0])
