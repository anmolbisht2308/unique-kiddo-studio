"""Kokoro TTS (Apache-2.0 model) with espeak-ng phonemes loaded via ctypes from the Piper bundle."""
import ctypes, glob, json, os, re
import numpy as np
import onnxruntime as ort

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")

def _load_espeak():
    lib = ctypes.cdll.LoadLibrary(sorted(glob.glob(f"{A}/piper/libespeak-ng.so*"))[0])
    if lib.espeak_Initialize(2, 0, ctypes.c_char_p(f"{A}/piper".encode()), 0) <= 0:
        raise RuntimeError("espeak init failed")
    lib.espeak_SetVoiceByName(b"en-us")
    lib.espeak_TextToPhonemes.restype = ctypes.c_char_p
    lib.espeak_TextToPhonemes.argtypes = [ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, ctypes.c_int]
    return lib

LIB = _load_espeak()
VOCAB = json.load(open(os.path.join(ROOT, "engine", "kokoro_vocab.json")))["vocab"]
SESS = ort.InferenceSession(f"{A}/kokoro-v1.0.onnx", providers=["CPUExecutionProvider"])
VOICES = np.load(f"{A}/voices-v1.0.bin")
PUNCT = r"[,.!?;:…—]"

def _ipa(chunk):
    buf = ctypes.create_string_buffer(chunk.encode("utf-8"))
    ptr = ctypes.c_char_p(ctypes.addressof(buf))
    out = []
    while ptr.value:
        r = LIB.espeak_TextToPhonemes(ctypes.byref(ptr), 1, 0x02)
        if r:
            out.append(r.decode("utf-8"))
    return " ".join(out).strip()

def phonemize(text):
    ph = ""
    for p in re.split(f"({PUNCT})", text):
        if not p.strip():
            continue
        ph = ph.rstrip() + p + " " if re.fullmatch(PUNCT, p) else ph + _ipa(p) + " "
    return "".join(c for c in ph.strip() if c in VOCAB)

def voice(spec=None):
    spec = spec or {"af_heart": 1.0}
    return sum(VOICES[k] * w for k, w in spec.items()) / sum(spec.values())

def tts(text, style, speed=0.9):
    toks = [VOCAB[c] for c in phonemize(text)][:510]
    audio = SESS.run(None, {"tokens": np.array([[0, *toks, 0]], dtype=np.int64),
                            "style": style[len(toks) - 1].astype(np.float32),
                            "speed": np.array([speed], dtype=np.float32)})[0]
    return np.asarray(audio, dtype=np.float32).reshape(-1), 24000
