"""Synthesised cartoon sound effects (all original, generated from scratch). Each returns a float array at SR."""
import numpy as np

SR = 44100
_rng = np.random.default_rng(11)


def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _sweep(f0, f1, dur, shape="lin"):
    t = _t(dur)
    f = f0 + (f1 - f0) * (t / dur if shape == "lin" else (t / dur) ** 2)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def _lp(x, a=0.15):
    """one-pole low-pass, a in (0,1]: smaller = darker"""
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc); y[i] = acc
    return y


def _noise(dur):
    return _rng.uniform(-1, 1, int(SR * dur))


def _env(n, attack=.005, decay=6.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-decay * t)


def _brass(f, dur, vib=0.0, vol=.3):
    t = _t(dur)
    ff = f * (1 + vib * np.sin(2 * np.pi * 5.5 * t))
    ph = 2 * np.pi * np.cumsum(ff) / SR
    x = sum(a * np.sin(ph * (n + 1)) for n, a in enumerate((1, .6, .4, .25, .15, .08)))
    env = np.minimum(1, t / .03) * np.minimum(1, (dur - t) / .06 + .0)
    return vol * x * np.clip(env, 0, 1) / 2.5


def pop():
    t = _t(.12); f = 300 + 900 * t / .12
    return .35 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-25 * t)


def tick():
    t = _t(.15)
    return .25 * np.sin(2 * np.pi * 880 * t) * np.exp(-30 * t)


def ding():
    t = _t(.9)
    a = .3 * np.sin(2 * np.pi * 1046.5 * t) * np.exp(-4 * t)
    b = np.zeros_like(a); s = int(.08 * SR)
    b[s:] = .25 * np.sin(2 * np.pi * 1318.5 * t[: len(t) - s]) * np.exp(-4 * t[: len(t) - s])
    return a + b


def boing():
    t = _t(.7)
    f = 140 + 220 * np.exp(-4 * t) + 45 * np.sin(2 * np.pi * 13 * t) * np.exp(-2 * t)
    return .45 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-3.5 * t)


def slide_up(dur=.6):
    return .3 * _sweep(350, 1500, dur, "sq") * np.exp(-1.2 * _t(dur))


def slide_down(dur=.7):
    return .3 * _sweep(1400, 250, dur) * np.exp(-1.0 * _t(dur))


def whoosh(dur=.4):
    n = _noise(dur); t = _t(dur)
    a = np.clip(.04 + .5 * np.sin(np.pi * t / dur), 0, 1)
    return .5 * _lp(n, .25) * a


def creak(dur=.5):
    t = _t(dur)
    f = 70 + 40 * np.sin(2 * np.pi * 3 * t) + 25 * _rng.standard_normal(len(t)).cumsum() / 400
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1) - 1
    grain = (np.sin(2 * np.pi * 38 * t) > .2).astype(float)
    return .16 * _lp(saw * grain, .3) * np.sin(np.pi * t / dur)


def drumroll(dur=1.2, crash=False):
    out = np.zeros(int(SR * (dur + (1.2 if crash else .1))))
    tt, i = 0.0, 0
    while tt < dur:
        rate = 14 + 16 * tt / dur
        hit = _noise(.05) * _env(int(SR * .05), .001, 60) * (.12 + .25 * tt / dur)
        a = int(tt * SR); out[a:a + len(hit)] += hit
        tt += 1 / rate; i += 1
    a = int(dur * SR)
    if crash:
        c = _noise(1.2) * _env(int(SR * 1.2), .002, 3.0) * .4
        c = c - _lp(c, .35)  # bright
        out[a:a + len(c)] += c
        k = np.sin(2 * np.pi * 70 * _t(.4)) * np.exp(-9 * _t(.4)) * .5
        out[a:a + len(k)] += k
    return out


def trombone():
    """wah wah wah waaah"""
    notes = [(311.1, .3, 0), (293.7, .3, 0), (277.2, .3, 0), (261.6, 1.0, .025)]
    out = []
    for f, d_, v in notes:
        x = _brass(f, d_, v, .32)
        out.append(_lp(x, .2) * 1.6)
    return np.concatenate(out)


def fanfare():
    seq = [(523.3, .13), (659.3, .13), (784.0, .13), (1046.5, .6)]
    out = [_brass(f, d_, .01 if d_ > .3 else 0, .3) for f, d_ in seq]
    x = np.concatenate(out)
    chord = sum(_brass(f, .6, .01, .14) for f in (523.3, 659.3, 784.0))
    x[-len(chord):] += chord
    return x


def sparkle():
    out = np.zeros(int(SR * 1.0))
    for j, f in enumerate((1568, 2093, 2637, 3136, 2637, 3136)):
        t = _t(.4); s = int(j * .07 * SR)
        out[s:s + len(t)] += .12 * np.sin(2 * np.pi * f * t) * np.exp(-8 * t)
    return out


def sizzle(dur=1.4):
    n = _noise(dur); hp = n - _lp(n, .5)
    crackle = (_rng.uniform(0, 1, len(n)) > .9993).astype(float)
    crack = np.convolve(crackle, np.exp(-np.arange(300) / 40), mode="same") * _noise(dur)
    t = _t(dur)
    return (.14 * hp + .35 * crack) * np.minimum(1, t / .05) * np.minimum(1, (dur - t) / .3)


def splash(dur=.7):
    n = _noise(dur)
    return .55 * _lp(n, .35) * _env(len(n), .004, 5.5)


def brrr(dur=.9):
    t = _t(dur)
    x = np.sign(np.sin(2 * np.pi * 95 * t)) * (0.5 + .5 * np.sin(2 * np.pi * 24 * t))
    return .18 * _lp(x, .2) * np.sin(np.pi * t / dur)


def pfft(dur=.55):
    t = _t(dur)
    x = _lp(_noise(dur), .08) * (0.6 + .4 * np.sin(2 * np.pi * 32 * t))
    return 1.4 * x * np.sin(np.pi * t / dur) ** .5


def bonk():
    t = _t(.35)
    return .5 * np.sin(2 * np.pi * (180 - 80 * t) * t) * np.exp(-14 * t) + \
        .2 * np.sin(2 * np.pi * 820 * t) * np.exp(-40 * t)


def roar(dur=1.0):
    t = _t(dur)
    x = _lp(_noise(dur), .05) * (0.5 + .5 * np.sin(2 * np.pi * 38 * t))
    x += .25 * np.sin(2 * np.pi * 85 * t + 3 * np.sin(2 * np.pi * 6 * t))
    return 1.2 * x * np.sin(np.pi * t / dur)


def buzz(dur=1.2):
    t = _t(dur)
    f = 210 + 25 * np.sin(2 * np.pi * 4 * t)
    ph = np.cumsum(f) / SR
    return .12 * _lp(2 * (ph % 1) - 1, .4) * (0.7 + .3 * np.sin(2 * np.pi * 9 * t))


def float_up(dur=1.2):
    t = _t(dur)
    return .22 * _sweep(500, 1300, dur) * (0.6 + .4 * np.sin(2 * np.pi * 7 * t)) * np.sin(np.pi * t / dur)


def crash():
    n = _noise(1.0)
    c = (n - _lp(n, .3)) * _env(len(n), .002, 4) * .5
    k = np.sin(2 * np.pi * 60 * _t(.5)) * np.exp(-8 * _t(.5)) * .6
    c[:len(k)] += k
    for j in range(5):  # clatter
        s = int((.08 + j * .09) * SR); b = bonk() * (.5 - j * .08)
        c[s:s + len(b)] += b[:len(c) - s]
    return c


def big_pop():
    t = _t(.25)
    return .6 * _noise(.25) * np.exp(-30 * t) + .4 * np.sin(2 * np.pi * (500 - 1400 * t) * t) * np.exp(-12 * t)


def chew():
    t = _t(.12)
    return .25 * _lp(_noise(.12), .2) * np.sin(np.pi * t / .12) * 3


def stretch(dur=2.2):
    t = _t(dur)
    f = 180 + 420 * (t / dur) ** 1.5
    return .14 * np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.7 + .3 * np.sin(2 * np.pi * 11 * t)) * np.minimum(1, t / .1)


def splat():
    return splash(.45) * 1.2


LIB = dict(crash=crash, big_pop=big_pop, chew=chew, stretch=stretch, splat=splat, pop=pop, tick=tick, ding=ding, boing=boing, slide_up=slide_up, slide_down=slide_down, whoosh=whoosh,
           creak=creak, drumroll=lambda: drumroll(1.1), drumroll_long=lambda: drumroll(1.7, crash=True),
           trombone=trombone, fanfare=fanfare, sparkle=sparkle, sizzle=sizzle, splash=splash, brrr=brrr,
           pfft=pfft, bonk=bonk, roar=roar, buzz=buzz, float_up=float_up)
_cache = {}


def get(name):
    if name not in _cache:
        _cache[name] = LIB[name]()
    return _cache[name]
