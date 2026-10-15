"""Unique Kiddo video engine.

Usage:  python3 engine/render.py episodes/ep002.json
Writes out/<id>/: video.mp4, thumbnail.png, subtitles.srt, script.md, upload.json
Formats: shadow | clues | learn | count  (see README.md for the episode file schema)
"""
import hashlib, json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from kiddo import kiddo, star_pts  # noqa: E402
import tts  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 44100
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI_DIR = os.path.join(ROOT, "assets", "noto", "2D", "png", "512")
DARK = (55, 45, 70)
ACCENT = (240, 90, 60)
PASTELS = [(205, 232, 255), (255, 226, 200), (214, 245, 200), (255, 214, 214), (255, 243, 190),
           (238, 220, 255), (200, 240, 245), (255, 228, 238), (225, 240, 205), (255, 235, 210)]
RAINBOW = [(255, 112, 98), (255, 170, 40), (60, 190, 120), (60, 140, 235), (170, 95, 220), (255, 95, 160)]
NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]

# ---------------------------------------------------------------- helpers
_fc = {}
def font(sz):
    sz = max(8, int(sz))
    if sz not in _fc:
        _fc[sz] = ImageFont.truetype(FONT, sz)
    return _fc[sz]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

def back_out(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def pop(t, start, dur=0.4):
    return 0.0 if t < start else back_out((t - start) / dur)

def wrap(text, sz, maxw):
    f = font(sz); lines = [""]
    for w in text.split():
        trial = (lines[-1] + " " + w).strip()
        if f.getlength(trial) <= maxw: lines[-1] = trial
        else: lines.append(w)
    return "\n".join(lines)

def fit_size(text, base, maxw):
    sz = base
    while sz > 40 and font(sz).getlength(text) > maxw:
        sz -= 4
    return sz

def emoji_path(ch):
    cps = [f"{ord(c):04x}" for c in ch if ord(c) != 0xFE0F]
    p = os.path.join(EMOJI_DIR, "emoji_u" + "_".join(cps) + ".png")
    if not os.path.exists(p):
        raise FileNotFoundError(f"No artwork for emoji {ch!r} ({p}). Pick a different emoji.")
    return p

_ec = {}
def emoji_img(ch, size, mode="color"):
    size = max(4, int(size) // 4 * 4)
    key = (ch, size, mode)
    if key not in _ec:
        im = Image.open(emoji_path(ch)).convert("RGBA").resize((size, size), Image.LANCZOS)
        if mode == "shadow":
            a = im.split()[3]
            im = Image.new("RGBA", im.size, (40, 40, 75, 255)); im.putalpha(a)
        _ec[key] = im
    return _ec[key]

def paste_emoji(img, ch, cx, cy, size, mode="color"):
    if size < 6: return
    e = emoji_img(ch, size, mode)
    img.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))

def bubble(d, x0, y0, x1, y1, tail_x, text, sz):
    d.rounded_rectangle([x0, y0, x1, y1], radius=40, fill=(255, 255, 255), outline=DARK, width=5)
    d.polygon([(tail_x - 25, y1 - 3), (tail_x + 25, y1 - 3), (tail_x - 20, y1 + 55)], fill=(255, 255, 255))
    d.line([(tail_x - 25, y1), (tail_x - 20, y1 + 55), (tail_x + 25, y1)], fill=DARK, width=5)
    d.multiline_text(((x0 + x1) / 2, (y0 + y1) / 2), text, font=font(sz), fill=DARK, anchor="mm",
                     align="center", spacing=12)

def big_text(d, xy, text, base, sc, fill=ACCENT, stroke=12):
    if sc <= 0.02: return
    d.text(xy, text, font=font(base * sc), fill=fill, anchor="mm", stroke_width=int(stroke * sc),
           stroke_fill=(255, 255, 255))

def letter_word(img, text, cx, cy, size, seed=1):
    f = font(size); widths = [f.getlength(c) for c in text]
    x = cx - sum(widths) / 2; rnd = random.Random(seed); ci = 0
    for ch, w in zip(text, widths):
        if ch != " ":
            pad = int(size * 0.4)
            tile = Image.new("RGBA", (int(w) + pad * 2, size + pad * 2), (0, 0, 0, 0))
            td = ImageDraw.Draw(tile)
            td.text((pad + w / 2 + size * .04, pad + size / 2 + size * .06), ch, font=f, fill=(55, 45, 70, 90),
                    anchor="mm", stroke_width=int(size * .09), stroke_fill=(55, 45, 70, 90))
            td.text((pad + w / 2, pad + size / 2), ch, font=f, fill=RAINBOW[ci % 6] + (255,), anchor="mm",
                    stroke_width=int(size * .08), stroke_fill=(255, 255, 255, 255))
            tile = tile.rotate(rnd.uniform(-9, 9), resample=Image.BICUBIC)
            img.alpha_composite(tile, (int(x - pad), int(cy - size / 2 - pad + rnd.uniform(-.06, .06) * size)))
            ci += 1
        x += w

random.seed(7)
DOTS = [(random.uniform(0, W), random.uniform(0, H), random.uniform(25, 90), random.uniform(.2, .6)) for _ in range(18)]
def background(img, base, t):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=base)
    light = tuple(min(255, c + 22) for c in base)
    for x, y, r, sp in DOTS:
        yy = (y - t * 40 * sp) % (H + 200) - 100
        d.ellipse([x - r, yy - r, x + r, yy + r], fill=light)
    d.rectangle([0, H - 170, W, H], fill=tuple(max(0, c - 30) for c in base))
    return d

def tone(f, dur, decay=6, vol=0.5, harm=(1, 0.4, 0.15)):
    tt = np.arange(int(SR * dur)) / SR
    return vol * sum(a * np.sin(2 * np.pi * f * (n + 1) * tt) for n, a in enumerate(harm)) * np.exp(-decay * tt)

def resample(x, sr):
    n = int(len(x) * SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)

# ---------------------------------------------------------------- timeline
class Timeline:
    def __init__(self, ep):
        self.ep = ep
        self.style = tts.voice(ep.get("voice"))
        self.speed = ep.get("speed", 0.9)
        self.clips, self.sfx, self.segments, self.subs = [], [], [], []

    def say(self, t, text):
        a, sr = tts.tts(text, self.style, self.speed)
        x = resample(a.astype(float), sr)
        nz = np.where(np.abs(x) > 0.01)[0]
        if len(nz): x = x[max(0, nz[0] - 800): nz[-1] + 1600]
        self.clips.append((t, x))
        end = t + len(x) / SR
        self.subs.append((t, end, text))
        return end

def build(ep):
    tl = Timeline(ep)
    think = ep.get("think_seconds", 5.0)
    repeat_gap = ep.get("repeat_seconds", 1.8)
    fmt = ep["format"]

    # intro
    if ep.get("intro"):
        tl.sfx += [(0.2, "pop"), (0.5, "pop"), (0.9, "pop")]
        e = 1.0
        for line in ep["intro"]:
            e = tl.say(e, line) + 0.4
        tl.segments.append(dict(kind="intro", start=0.0, end=e + 0.6))
        t = e + 0.6
    else:  # hook mode: open straight on the first round
        t = 0.0

    items = ep["items"]
    for i, it in enumerate(items):
        s = t; seg = dict(kind="item", i=i, start=s, item=it, bg=tuple(it.get("bg", PASTELS[i % len(PASTELS)])))
        name = it["name"]; say_name = it.get("say", name)
        if fmt in ("shadow", "clues", "letter"):
            tl.sfx += [(s + 0.3, "pop")]
            if fmt == "letter":
                tl.sfx += [(s + 0.6, "pop")]
                e = s + 0.9
                default_q = f"Which one starts with {it['letter']}?"
            elif fmt == "clues":
                tl.sfx += [(s + 0.8, "pop")]
                e = tl.say(s + 0.9, f"Look! {it['clue_text']}!") + 0.4
                default_q = "Who uses these? Can you guess?"
            else:
                e = s + 0.9
                default_q = "Whose shadow is this? Can you guess?"
            seg["ask"] = e
            e = tl.say(e, it.get("ask", default_q))
            if it.get("hint"):
                e = tl.say(e + 0.4, it["hint"])
            seg["think"] = e + 0.3
            seg["reveal"] = seg["think"] + think
            r = seg["reveal"]
            tl.sfx += [(seg["think"] + think - 3, "tick"), (seg["think"] + think - 2, "tick"),
                       (seg["think"] + think - 1, "tick"), (r, "ding")]
            e = tl.say(r + 0.5, it.get("reveal_line", f"Yes! It's {say_name}!"))
        elif fmt == "learn":
            tl.sfx += [(s + 0.3, "pop")]
            seg["reveal"] = s + 0.3
            e = tl.say(s + 0.8, it.get("reveal_line", f"Look! This is {say_name}!"))
        elif fmt == "count":
            n = int(it["count"]); plural = it.get("plural", name.lower() + "s")
            tl.sfx += [(s + 0.3, "pop")]
            e = tl.say(s + 0.6, it.get("ask", f"How many {plural} can you see? Let's count together!"))
            seg["count_times"] = []
            e += 0.5
            for k in range(1, n + 1):
                seg["count_times"].append(e)
                tl.sfx.append((e, "pop"))
                e = max(e + 1.0, tl.say(e, NUM_WORDS[k].capitalize() + "!") + 0.35)
            seg["reveal"] = e
            tl.sfx.append((e, "ding"))
            e = tl.say(e + 0.3, it.get("reveal_line", f"{NUM_WORDS[n].capitalize()} {plural if n != 1 else name.lower()}!"))
            name = str(n)
        seg["say_t"] = e + 0.5
        e = tl.say(seg["say_t"], it.get("say_line") or f"Say it with me! {NUM_WORDS[int(name)].capitalize() if name.isdigit() else name}!")
        seg["repeat"] = e
        seg["fact_t"] = e + repeat_gap
        e = tl.say(seg["fact_t"], it["fact"]) if it.get("fact") else seg["fact_t"]
        seg["end"] = e + 1.2
        seg["label"] = name
        tl.segments.append(seg); t = seg["end"]

    # outro
    s = t; tl.sfx.append((s, "pop")); e = s + 0.6
    for line in ep["outro"]:
        e = tl.say(e, line) + 0.5
    bye = e + 0.5
    if ep.get("bye", True):
        tl.sfx.append((bye, "ding"))
        e = tl.say(bye, "Bye bye! See you next time!")
    else:
        bye = 1e9
    tl.segments.append(dict(kind="outro", start=s, end=e + 1.5, bye=bye))
    tl.duration = tl.segments[-1]["end"]
    return tl

# ---------------------------------------------------------------- frames
def frame(tl, t):
    ep = tl.ep
    seg = next((g for g in tl.segments if g["start"] <= t < g["end"]), tl.segments[-1])
    lt = t - seg["start"]
    img = Image.new("RGBA", (W, H))
    if seg["kind"] == "intro":
        d = background(img, tuple(ep.get("intro_bg", (255, 236, 200))), t)
        l1, l2 = ep["title_screen"]
        big_text(d, (W / 2, 330), l1, fit_size(l1, 150, 980), pop(t, .2, .5), (240, 90, 60), 10)
        big_text(d, (W / 2, 490), l2, fit_size(l2, 150, 980), pop(t, .5, .5), (60, 120, 230), 10)
        kiddo(d, W / 2, 1320, 330 * pop(t, .9, .5), t, wave=True)
        if t > 1.0:
            bubble(d, 120, 690, 960, 940, W / 2, "Hello, little friends!\nLet's play!", 56)
        return img
    if seg["kind"] == "outro":
        d = background(img, (230, 220, 255), t)
        kiddo(d, W / 2, 1320, 330 * pop(lt, 0, .5), t, wave=True)
        bubble(d, 100, 420, 980, 760, W / 2, ep.get("outro_screen", "Great job, friends!"), 62)
        if t >= seg["bye"]:
            big_text(d, (W / 2, 900), "Bye bye!", 110, pop(t, seg["bye"], .5), ACCENT, 9)
        return img

    it = seg["item"]; i = seg["i"]; fmt = ep["format"]
    d = background(img, seg["bg"], t)
    if ep.get("hook_text") and i == 0 and t < seg["reveal"]:
        lt += 0.75  # first frame already shows the puzzle
        big_text(d, (W / 2, 150), ep["hook_text"], fit_size(ep["hook_text"], 96, 1000), 1.0, ACCENT, 8)
    else:
        d.text((W / 2, 150), f"{ep.get('round_word', 'ROUND')} {i + 1} of {len(ep['items'])}", font=font(56),
               fill=DARK, anchor="mm")
    revealed = t >= seg["reveal"]
    cx, cy = W / 2, 700

    if fmt == "shadow":
        sc = pop(lt, .3, .45)
        r = 300 * sc
        if sc > .02:
            d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=60 * sc, fill=(255, 255, 255),
                                outline=DARK, width=max(2, int(7 * sc)))
        if revealed:
            paste_emoji(img, it["emoji"], cx, cy, 470 * pop(t, seg["reveal"], .45))
        else:
            paste_emoji(img, it["emoji"], cx, cy, 470 * sc, "shadow")
    elif fmt == "clues":
        k = clamp((t - seg["reveal"]) / .4) if revealed else 0
        for j, ch in enumerate(it["clues"]):
            s2 = pop(lt, .3 + j * .5, .4) * (1 - .45 * k)
            x = cx + (-235 if j == 0 else 235) * (1 - .1 * k); y = 520 - 230 * k
            r = 200 * s2
            if s2 > .02:
                d.rounded_rectangle([x - r, y - r, x + r, y + r], radius=50 * s2, fill=(255, 255, 255),
                                    outline=DARK, width=max(2, int(6 * s2)))
                paste_emoji(img, ch, x, y, 300 * s2)
        if revealed:
            paste_emoji(img, it["emoji"], cx, 790, 420 * pop(t, seg["reveal"] + .2, .45))
    elif fmt == "letter":
        L = it["letter"]
        sc = pop(lt, .3, .45)
        R = 170 * sc
        if sc > .02:
            d.ellipse([cx - R, 420 - R, cx + R, 420 + R], fill=(255, 255, 255), outline=DARK, width=max(2, int(8 * sc)))
            big_text(d, (cx, 412), L + L.lower(), 190, sc, (60, 120, 230), 10)
        k = clamp((t - seg["reveal"]) / .45) if revealed else 0
        opts = [(it["emoji"], True), (it["wrong"], False)]
        if it.get("correct_side", "left") == "right": opts.reverse()
        for j, (ch, ok) in enumerate(opts):
            s2 = pop(lt, .6, .4)
            x0 = cx + (-250 if j == 0 else 250)
            if ok:
                x = x0 + (cx - x0) * k; y = 830 + 0 * k; s2 *= 1 + .25 * k
            else:
                x = x0; y = 830; s2 *= (1 - k)
            r = 190 * s2
            if s2 > .02:
                d.rounded_rectangle([x - r, y - r, x + r, y + r], radius=48 * s2,
                                    fill=(225, 255, 225) if ok and k > 0 else (255, 255, 255),
                                    outline=(60, 170, 90) if ok and k > 0 else DARK, width=max(2, int(7 * s2)))
                paste_emoji(img, ch, x, y, 290 * s2)
    elif fmt == "learn":
        sc = pop(lt, .3, .5)
        r = 300 * sc
        if sc > .02:
            d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=60 * sc, fill=(255, 255, 255),
                                outline=DARK, width=max(2, int(7 * sc)))
        paste_emoji(img, it["emoji"], cx, cy + math.sin(t * 2) * 6, 470 * sc)
    elif fmt == "count":
        n = int(it["count"]); cols = 3 if n > 4 else 2 if n > 1 else 1
        rows = math.ceil(n / cols); size = 230 if n > 4 else 280
        gap = size + 40; x0 = cx - (cols - 1) * gap / 2; y0 = 700 - (rows - 1) * gap / 2
        for k in range(n):
            x = x0 + (k % cols) * gap; y = y0 + (k // cols) * gap
            paste_emoji(img, it["emoji"], x, y, size * pop(lt, .3 + k * .08, .35))
            ct = seg["count_times"][k]
            if t >= ct:
                p = pop(t, ct, .3)
                d.ellipse([x + size / 2 - 70, y - size / 2 - 10, x + size / 2 + 10, y - size / 2 + 70],
                          fill=(255, 205, 45), outline=DARK, width=4)
                d.text((x + size / 2 - 30, y - size / 2 + 30), str(k + 1), font=font(56 * max(p, .3)),
                       fill=DARK, anchor="mm")

    label_y = 1150 if fmt != "clues" else 1100
    if fmt in ("shadow", "clues", "letter") and not revealed:
        if t >= seg["think"]:
            tt = t - seg["think"]; total = seg["reveal"] - seg["think"]
            bubble(d, 360, 1230, 1030, 1450, 470, "Hmm... think!" + "." * (1 + int(tt * 2.5) % 3), 64)
            R = 110; ry = label_y
            d.ellipse([cx - R, ry - R, cx + R, ry + R], fill=(255, 255, 255), outline=DARK, width=6)
            prog = clamp(tt / total)
            if prog < 1:
                d.pieslice([cx - R + 14, ry - R + 14, cx + R - 14, ry + R - 14], -90 + 360 * prog, 270,
                           fill=(255, 205, 45))
            n = math.ceil(total - tt)
            if n <= 3:
                big_text(d, (cx, ry), str(n), 120, pop(tt, total - n, .25), ACCENT, 8)
            else:
                d.text((cx, ry), "?", font=font(120), fill=ACCENT, anchor="mm", stroke_width=8,
                       stroke_fill=(255, 255, 255))
        elif t >= seg.get("ask", 1e9) - .1:
            q = it.get("ask_screen", "Whose shadow\nis this?" if fmt == "shadow" else
                       f"Which one starts\nwith {it['letter']}?" if fmt == "letter" else "Who uses\nthese?")
            bubble(d, 360, 1230, 1030, 1450, 470, q if "\n" in q else wrap(q, 64, 600), 64)
    elif revealed:
        label = seg["label"].upper()
        pulse = 1 + .08 * math.sin((t - seg["repeat"]) * 8) if seg["repeat"] <= t < seg["fact_t"] else 1
        if fmt == "count" and t < seg["reveal"]:
            pass
        else:
            big_text(d, (cx, label_y), label, fit_size(label, 140, 960), pop(t, seg["reveal"], .45) * pulse)
        if seg["say_t"] <= t < seg["fact_t"]:
            bubble(d, 360, 1230, 1030, 1450, 470, "Say it\nwith me!", 64)
        elif t >= seg["fact_t"] and it.get("fact"):
            bubble(d, 360, 1230, 1030, 1450, 470, wrap(it.get("fact_screen", it["fact"]), 52, 600), 52)
    elif fmt == "count":
        bubble(d, 360, 1230, 1030, 1450, 470, "Let's count!", 64)
    kiddo(d, 220, 1620, 220, t, wave=(seg["say_t"] <= t < seg["fact_t"]))
    return img

# ---------------------------------------------------------------- audio
def mix_audio(tl, path):
    N = int(SR * tl.duration)
    voice = np.zeros(N + SR)
    for st, x in tl.clips:
        a = int(st * SR); voice[a:a + len(x)] += x
    voice = voice[:N]; voice /= max(1e-9, np.abs(voice).max()) / .9
    music = np.zeros(N + SR)
    def add(sig, at):
        a = int(at * SR); music[a:a + len(sig)] += sig[: len(music) - a]
    h = int(hashlib.md5(tl.ep["id"].encode()).hexdigest(), 16)
    progs = [[[261.6, 329.6, 392.0, 523.3], [196.0, 246.9, 293.7, 392.0], [220.0, 261.6, 329.6, 440.0], [174.6, 220.0, 261.6, 349.2]],
             [[293.7, 370.0, 440.0, 587.3], [246.9, 293.7, 370.0, 493.9], [196.0, 246.9, 293.7, 392.0], [220.0, 277.2, 329.6, 440.0]],
             [[349.2, 440.0, 523.3, 698.5], [293.7, 349.2, 440.0, 587.3], [233.1, 293.7, 349.2, 466.2], [261.6, 329.6, 392.0, 523.3]]]
    pats = [[0, 1, 2, 3, 2, 1, 2, 3], [0, 2, 1, 3, 0, 2, 3, 2], [0, 1, 2, 1, 3, 2, 1, 2]]
    chords = progs[h % 3]; pat = pats[(h // 3) % 3]; beat = 60 / (96 + h % 16) / 2
    tp, n = 0.0, 0
    while tp < tl.duration - .5:
        ch = chords[(n // 8) % 4]
        add(tone(ch[pat[n % 8]], .6, decay=5, vol=.08), tp)
        if n % 8 == 0: add(tone(ch[0] / 2, 1.2, decay=2.5, vol=.07, harm=(1, .2)), tp)
        tp += beat; n += 1
    for at, kind in tl.sfx:
        if kind == "pop":
            tt = np.arange(int(SR * .12)) / SR; f = 300 + 900 * tt / .12
            add(.35 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-25 * tt), at)
        elif kind == "tick": add(tone(880, .15, decay=30, vol=.25), at)
        elif kind == "ding":
            add(tone(1046.5, .9, decay=4, vol=.3), at); add(tone(1318.5, .9, decay=4, vol=.25), at + .08)
    music = music[:N]; music /= max(1e-9, np.abs(music).max())
    fade = int(SR * 1.5); music[-fade:] *= np.linspace(1, 0, fade)
    env = np.convolve((np.abs(voice) > .02).astype(float), np.ones(int(SR * .25)) / (SR * .25), mode="same")
    mix = music * (.5 - .3 * np.clip(env * 3, 0, 1)) + voice
    mix /= np.abs(mix).max() / .9
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

# ---------------------------------------------------------------- extras
def thumbnail(ep, path):
    img = Image.new("RGBA", (W, H)); d = background(img, tuple(ep.get("intro_bg", (255, 226, 200))), 0)
    l1, l2 = ep["title_screen"]
    letter_word(img, l1, W / 2, 260, fit_size(l1, 180, 1000), seed=2)
    letter_word(img, l2, W / 2, 470, fit_size(l2, 160, 1000), seed=9)
    mode = "shadow" if ep["format"] == "shadow" else "color"
    for k, it in enumerate(ep["items"][:4]):
        x = 290 if k % 2 == 0 else 790; y = 820 if k < 2 else 1220; r = 190
        d.rounded_rectangle([x - r, y - r, x + r, y + r], radius=48, fill=(255, 255, 255), outline=DARK, width=8)
        paste_emoji(img, it["emoji"], x, y, 300, mode)
    d.ellipse([W / 2 - 110, 910, W / 2 + 110, 1130], fill=(255, 205, 45), outline=DARK, width=8)
    d.text((W / 2, 1020), "?", font=font(170), fill=ACCENT, anchor="mm", stroke_width=8, stroke_fill=(255, 255, 255))
    kiddo(d, W / 2, 1640, 300, 0.0, blink_ok=False)
    img.convert("RGB").save(path)

def srt(tl, path):
    def ts(x): return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(x % 1 * 1000):03d}"
    with open(path, "w") as f:
        for k, (a, b, text) in enumerate(tl.subs, 1):
            f.write(f"{k}\n{ts(a)} --> {ts(b)}\n{text}\n\n")

def main(ep_path, preview=None):
    ep = json.load(open(ep_path))
    out = os.path.join(ROOT, "out", ep["id"]); os.makedirs(out, exist_ok=True)
    tl = build(ep)
    print(f"{ep['id']}: {len(ep['items'])} items, length {tl.duration:.1f}s")
    if tl.duration > 179 and ep.get("vertical", True):
        print("WARNING: over 3:00, will not count as a Short")
    if preview:
        sheet = Image.new("RGB", (300 * len(preview), 533))
        for k, ts_ in enumerate(preview):
            sheet.paste(frame(tl, ts_).convert("RGB").resize((300, 533)), (300 * k, 0))
        sheet.save(os.path.join(out, "preview.png")); print("preview:", os.path.join(out, "preview.png"))
        for g in tl.segments[:3]:
            print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in g.items() if k != "item"})
        return
    apath = os.path.join(out, "audio.wav"); mix_audio(tl, apath)
    vpath = os.path.join(out, "video.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-i", apath, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
                             vpath], stdin=subprocess.PIPE)
    for fi in range(int(tl.duration * FPS)):
        proc.stdin.write(frame(tl, fi / FPS).convert("RGB").tobytes())
    proc.stdin.close(); proc.wait(); os.remove(apath)
    thumbnail(ep, os.path.join(out, "thumbnail.png"))
    srt(tl, os.path.join(out, "subtitles.srt"))
    with open(os.path.join(out, "script.md"), "w") as f:
        f.write(f"# {ep['seo']['title']}\n\n| Time | Narration |\n|---|---|\n")
        for a, _, text in tl.subs:
            f.write(f"| {int(a // 60)}:{int(a % 60):02d} | {text} |\n")
    json.dump(dict(ep["seo"], duration=round(tl.duration, 1)), open(os.path.join(out, "upload.json"), "w"), indent=2,
              ensure_ascii=False)
    print("done:", vpath, f"{tl.duration:.1f}s", "ffmpeg rc", proc.returncode)

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 1 and args[1] == "--preview":
        main(args[0], [float(x) for x in args[2:]])
    else:
        main(args[0])
