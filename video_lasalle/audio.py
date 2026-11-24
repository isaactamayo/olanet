"""Música de fondo alegre + efectos + voces, con la música bajando cuando hablan las niñas.
Uso: python3 audio.py <dir_build>   (lee events.json y voces.wav; escribe audio_final.wav)
"""
import json, sys, os
import numpy as np, soundfile as sf

B = sys.argv[1]
d = json.load(open(os.path.join(B, "events.json")))
T = d["TOTAL"]; SR = 44100; N = int(T * SR)
rng = np.random.default_rng(3)
mus = np.zeros(N); fx = np.zeros(N)


def add(buf, sig, t, g=1.0):
    i = int(t * SR)
    if i >= N or i < 0: return
    sig = sig[:N - i]; buf[i:i + len(sig)] += sig * g


def tt(dur): return np.arange(int(dur * SR)) / SR


def pluck(f, dur=0.9):  # guitarra/ukelele suave (síntesis aditiva)
    t = tt(dur); s = sum(np.sin(2*np.pi*k*f*t) * np.exp(-t*(2.5 + k*1.8)) / k**1.2 for k in range(1, 7))
    return s * np.minimum(1, t / 0.004)


def bell(f, dur=1.4):  # glockenspiel
    t = tt(dur)
    s = np.sin(2*np.pi*f*t)*np.exp(-t*3) + 0.35*np.sin(2*np.pi*f*2.76*t)*np.exp(-t*7) + 0.15*np.sin(2*np.pi*f*5.4*t)*np.exp(-t*12)
    return s * np.minimum(1, t / 0.002)


def bass(f, dur):
    t = tt(dur); return (np.sin(2*np.pi*f*t) + 0.3*np.sin(4*np.pi*f*t)) * np.minimum(1, t/0.01) * np.exp(-t*1.5)


def noise(dur): return rng.normal(0, 1, int(dur * SR))


NOTE = lambda n: 440 * 2 ** ((n - 69) / 12)
# ---------------- música: 104 bpm, C G Am F ----------------
bpm = 104; beat = 60 / bpm
CH = [(48, [60, 64, 67]), (43, [59, 62, 67]), (45, [60, 64, 69]), (41, [60, 65, 69])]
MEL = [[76, 79, 76, 72], [74, 79, 71, 74], [72, 76, 81, 79], [77, 76, 74, 72],
       [76, 79, 84, 83], [81, 79, 74, 76], [72, 76, 79, 81], [77, 74, 72, 0]]
t = 0.0; bar = 0
while t < T - 2:
    root, ch = CH[bar % 4]
    add(mus, bass(NOTE(root), beat * 2), t, 0.35); add(mus, bass(NOTE(root + 7), beat * 2), t + 2*beat, 0.28)
    arp = [ch[0], ch[1], ch[2], ch[1] + 12, ch[2], ch[1], ch[0] + 12, ch[1]]
    for k, n in enumerate(arp):
        add(mus, pluck(NOTE(n)), t + k * beat / 2, 0.11 if k % 2 == 0 else 0.08)
    for k in range(4):  # shaker suave
        n = noise(0.05) * np.exp(-tt(0.05) * 60); add(mus, np.diff(n, prepend=0), t + k*beat + beat/2, 0.05)
    if (bar // 8) % 2 == 1:  # melodía en secciones alternas
        for k, n in enumerate(MEL[bar % 8]):
            if n: add(mus, bell(NOTE(n)), t + k * beat, 0.09)
    t += 4 * beat; bar += 1
fo = int(3 * SR); mus[-fo:] *= np.linspace(1, 0, fo)
fi = int(0.8 * SR); mus[:fi] *= np.linspace(0, 1, fi)

# ---------------- efectos ----------------
for e in d["EVENTS"]:
    k, t0 = e["k"], e["t"]
    if k == "pop":
        tt_ = tt(0.12); f = np.linspace(420, 980, len(tt_)); add(fx, np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-tt_*25), t0, 0.22)
    elif k == "tick":
        tt_ = tt(0.06); add(fx, np.sin(2*np.pi*1500*tt_) * np.exp(-tt_*80), t0, 0.08)
    elif k == "ding":
        add(fx, bell(NOTE(88), 1.2), t0, 0.16); add(fx, bell(NOTE(95), 1.0), t0 + 0.08, 0.10)
    elif k == "chime":
        for i, n in enumerate([84, 88, 91, 96, 100]): add(fx, bell(NOTE(n), 0.9), t0 + i * 0.06, 0.08)
    elif k == "whoosh":
        n = noise(0.6); n = np.convolve(n, np.ones(40) / 40, "same"); add(fx, n * np.hanning(len(n)), max(0, t0 - 0.3), 0.5)
    elif k == "stamp":
        tt_ = tt(0.35); add(fx, np.sin(2*np.pi*np.cumsum(np.linspace(150, 50, len(tt_)))/SR) * np.exp(-tt_*10), t0 + 0.12, 0.6)
        add(fx, noise(0.1) * np.exp(-tt(0.1)*40), t0 + 0.12, 0.2)
    elif k == "chalk":
        n = noise(0.45); n = np.diff(np.diff(n, prepend=0), prepend=0); env = np.abs(np.sin(tt(0.45) * 2*np.pi*6))
        add(fx, n * env * np.exp(-tt(0.45)*2), t0, 0.04)

# ---------------- voces + ducking ----------------
v24, vsr = sf.read(os.path.join(B, "voces.wav"))
voz = np.interp(np.arange(N) / SR, np.arange(len(v24)) / vsr, v24)  # 24 kHz -> 44,1 kHz
def media_movil(x, n):  # rápida, con suma acumulada
    c = np.cumsum(np.concatenate([np.zeros(n // 2 + 1), x, np.zeros(n)]))
    return (c[n:n + len(x)] - c[:len(x)]) / n


act = (media_movil((np.abs(voz) > 0.02).astype(float), int(0.25 * SR)) > 0).astype(float)
duck = 1 - 0.55 * media_movil(media_movil(act, int(0.2 * SR)), int(0.2 * SR))
mix = voz * 1.0 + mus * duck * 0.55 + fx * 0.7
mix /= max(1e-9, np.abs(mix).max()) / 0.95
sf.write(os.path.join(B, "audio_final.wav"), np.stack([mix, mix], 1), SR, subtype="PCM_16")
print("ok", T)
