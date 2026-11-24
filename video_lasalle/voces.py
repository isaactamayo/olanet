"""Genera las voces de Ángeles y Natalia y la línea de tiempo del vídeo.

Uso: [MOTOR=edge|kokoro] python3 voces.py <dir_modelos> <dir_salida>
  edge (por defecto): voces neuronales de Microsoft vía edge-tts (requiere acceso a speech.platform.bing.com)
  kokoro: offline; dir_modelos contiene kokoro.onnx y voices.bin (github.com/thewh1teagle/kokoro-onnx, model-files-v1.0)
Salida: voces.wav (pista de voz), timeline.js (tiempos + apertura de boca por fotograma)
"""
import json, sys, os, subprocess, tempfile, asyncio
import numpy as np, soundfile as sf

MOD, OUT = sys.argv[1], sys.argv[2]
MOTOR = os.environ.get("MOTOR", "edge")  # "edge" (voces neuronales de Microsoft) o "kokoro" (offline)
HERE = os.path.dirname(os.path.abspath(__file__))
SR, FPS = 24000, 24
GAP, SCENE_IN, SCENE_OUT = 0.3, 0.9, 0.9

if MOTOR == "edge":
    import edge_tts
    # Cada niña tiene su propia voz; se sube el tono y algo los formantes para que suene infantil
    VOCES = {
        "L": dict(voice="es-ES-XimenaNeural", rate="+12%", pitch="+22Hz", shift=1.07),  # Ángeles
        "M": dict(voice="es-ES-ElviraNeural", rate="+8%", pitch="+30Hz", shift=1.08),  # Natalia
    }

    def voz_cruda(who, txt, wav):
        v = VOCES[who]
        mp3 = wav + ".mp3"
        for intento in range(4):
            try:
                asyncio.run(edge_tts.Communicate(txt, v["voice"], rate=v["rate"], pitch=v["pitch"], proxy=os.environ.get("HTTPS_PROXY")).save(mp3)); break
            except Exception:
                if intento == 3: raise
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", str(SR), "-ac", "1", wav], check=True)
        return SR
else:
    from kokoro_onnx import Kokoro
    VOCES = {"L": dict(speed=1.08, shift=1.24), "M": dict(speed=1.00, shift=1.15)}
    k = Kokoro(os.path.join(MOD, "kokoro.onnx"), os.path.join(MOD, "voices.bin"))
    dora, bella = k.get_voice_style("ef_dora"), k.get_voice_style("af_bella")
    estilos = {"L": dora, "M": dora * 0.85 + bella * 0.15}

    def voz_cruda(who, txt, wav):
        s, sr = k.create(txt, voice=estilos[who], speed=VOCES[who]["speed"], lang="es")
        sf.write(wav, s, sr); return sr


def sintetiza(who, txt):
    f = VOCES[who]["shift"]
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        sr = voz_cruda(who, txt, a)
        # asetrate sube tono y formantes (tracto vocal más corto = voz infantil); atempo recupera la duración
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a, "-af",
                        f"asetrate={int(sr*f)},aresample={SR},atempo={1/f:.5f},"
                        "highpass=f=120,equalizer=f=3500:t=q:w=1:g=2",
                        "-ac", "1", b], check=True)
        out, _ = sf.read(b)
    thr = 0.01 * np.abs(out).max()
    idx = np.where(np.abs(out) > thr)[0]
    out = out[max(0, idx[0] - 600): idx[-1] + 1200]
    return out / (np.abs(out).max() + 1e-9) * 0.9


def envolvente(sig):
    """Apertura de boca 0..1 por fotograma."""
    hop = SR // FPS
    n = int(np.ceil(len(sig) / hop))
    rms = np.array([np.sqrt(np.mean(sig[i*hop:(i+1)*hop] ** 2)) if len(sig[i*hop:(i+1)*hop]) else 0 for i in range(n)])
    rms = rms / (np.percentile(rms, 95) + 1e-9)
    return [round(float(min(1, max(0, (x - 0.08) * 1.3))), 2) for x in rms]


guion = json.load(open(os.path.join(HERE, "guion.json")))
t = 0.6
pista = []
escenas = []
for e in guion["escenas"]:
    esc = {"id": e["id"], "titulo": e["titulo"], "start": round(t, 3), "lineas": []}
    t += SCENE_IN
    for ln in e["lineas"]:
        txt = ln.get("tts", ln["text"])
        if ln["who"] == "A":
            a, b = sintetiza("L", txt), sintetiza("M", txt)
            n = max(len(a), len(b))
            sig = (np.pad(a, (0, n - len(a))) + np.pad(b, (0, n - len(b)))) * 0.6
            env = {"L": envolvente(a), "M": envolvente(b)}
        else:
            sig = sintetiza(ln["who"], txt)
            env = {ln["who"]: envolvente(sig)}
        dur = len(sig) / SR
        pista.append((t, sig))
        esc["lineas"].append({"who": ln["who"], "text": ln["text"], "start": round(t, 3), "dur": round(dur, 3), "env": env})
        print(f"{t:7.2f}s {ln['who']} {dur:5.2f}s  {ln['text'][:60]}")
        t += dur + GAP
    t += SCENE_OUT - GAP
    esc["dur"] = round(t - esc["start"], 3)
    escenas.append(esc)

TOTAL = round(t + 3.5, 2)  # cola final para el cartel de cierre
voz = np.zeros(int(TOTAL * SR) + SR)
for t0, s in pista:
    i = int(t0 * SR)
    voz[i:i + len(s)] += s
sf.write(os.path.join(OUT, "voces.wav"), voz[:int(TOTAL * SR)], SR)
with open(os.path.join(OUT, "timeline.js"), "w") as f:
    f.write("window.TL=" + json.dumps({"total": TOTAL, "fps": FPS, "escenas": escenas}, ensure_ascii=False) + ";\n")
print("TOTAL", TOTAL)
