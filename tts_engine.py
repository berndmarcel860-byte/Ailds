# -*- coding: utf-8 -*-
"""
============================================================
🗣️ Coqui XTTSv2 / Thorsten Hybrid TTS Engine (GPU Optimized)
============================================================
- Vollständige GPU-Unterstützung (float16)
- XTTSv2 Voice Cloning mit REFERENCE_WAV
- Automatisches Atem-Einfügen für natürliches Sprechen
- Saubere Satzaufteilung (keine Fremdsprache am Satzende)
- Parallele Generierung für nahtlose Übergänge
- 8 kHz PCM WAV für Asterisk
============================================================
"""

import os, re, hashlib, subprocess, time, torch, threading
from pathlib import Path
from dotenv import load_dotenv
from TTS.api import TTS

# ============================================================
# ⚙️ Environment Setup
# ============================================================
load_dotenv()
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["COQUI_TTS_CACHE"] = os.getenv("COQUI_CACHE_DIR", "/root/.local/share/tts")

# ============================================================
# 📁 Pfade
# ============================================================
ASTERISK_SOUNDS_DIR = Path(os.getenv("ASTERISK_SOUNDS_DIR", "/var/lib/asterisk/sounds"))
SOUNDS_MAIN = ASTERISK_SOUNDS_DIR / "aiagent"
SOUNDS_MAIN.mkdir(parents=True, exist_ok=True)

BREATH_WAV = Path(os.getenv("BREATH_WAV", "/var/lib/asterisk/sounds/aiagent/breath1.wav"))
REFERENCE_WAV = os.getenv("REFERENCE_WAV", "/var/lib/asterisk/sounds/aiagent/de_f_short.wav")

# ============================================================
# 🔧 Modelle
# ============================================================
TTS_ENGINE = os.getenv("TTS_ENGINE", "xttsv2").lower()
LANG = os.getenv("LANGUAGE", "de")

MODEL_THORSTEN = os.getenv("COQUI_MODEL_THORSTEN", "tts_models/de/thorsten/vits-neon")
MODEL_XTTSV2 = os.getenv("COQUI_MODEL_XTTSV2", "tts_models/multilingual/multi-dataset/xtts_v2")

# ============================================================
# 🧠 GPU Setup
# ============================================================
use_gpu = torch.cuda.is_available()
device = "cuda" if use_gpu else "cpu"
compute_type = "float16" if use_gpu else "int8"
print(f"🧠 Init Coqui TTS auf {torch.cuda.get_device_name(0) if use_gpu else 'CPU'} (GPU={'Ja' if use_gpu else 'Nein'})")

# ============================================================
# 🗣️ Modell-Laden
# ============================================================
tts_model = None
try:
    if TTS_ENGINE == "xttsv2":
        print(f"🗣️ Lade XTTSv2 Modell: {MODEL_XTTSV2}")
        tts_model = TTS(model_name=MODEL_XTTSV2, progress_bar=False)
        tts_model.to(device)
        if REFERENCE_WAV and os.path.exists(REFERENCE_WAV):
            print(f"🎧 Voice Reference geladen: {REFERENCE_WAV}")
        else:
            print("⚠️ Kein REFERENCE_WAV gefunden – Standardstimme wird genutzt.")
        # Warmup
        tts_model.tts_to_file(
            text="Warmup",
            file_path="/tmp/tts_warmup.wav",
            speaker_wav=REFERENCE_WAV if os.path.exists(REFERENCE_WAV) else None,
            language=LANG
        )
        print("🔥 XTTSv2 Warmup abgeschlossen.")
    else:
        print(f"🗣️ Lade Thorsten Modell: {MODEL_THORSTEN}")
        tts_model = TTS(model_name=MODEL_THORSTEN, progress_bar=False)
        tts_model.to(device)
        _ = tts_model.tts("Warmup")
        print("🔥 Thorsten Warmup abgeschlossen.")
    print("✅ TTS Modell erfolgreich geladen.")
except Exception as e:
    print(f"❌ Fehler beim Laden des Modells ({TTS_ENGINE}): {e}")

# ============================================================
# 🧹 Hilfsfunktionen
# ============================================================
def sanitize_text(text: str) -> str:
    """Bereinigt Text für XTTSv2 – verhindert Sprachmischung"""
    text = text.strip()
    text = re.sub(r"[\u202C\u200B\uFEFF]+", "", text)
    text = text.replace("„", "").replace("“", "").replace('"', "")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("..", ".").replace("...", "…")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def split_sentences(text: str):
    """Sauberes Satz-Splitting für Coqui"""
    text = sanitize_text(text)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜa-zäöüß])', text)
    return [sanitize_text(s) for s in sentences if len(s.strip()) > 2]

def wav_path(sentence: str) -> Path:
    return SOUNDS_MAIN / f"tts_{hashlib.md5(sentence.encode()).hexdigest()}.wav"

def convert_to_asterisk(raw_path: Path, out_path: Path):
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "wav", "-i", str(raw_path),
        "-ac", "1", "-ar", "8000", "-acodec", "pcm_s16le", str(out_path)
    ], check=True)
    raw_path.unlink(missing_ok=True)

# ============================================================
# 🔊 Atem hinzufügen
# ============================================================
def add_breath_after(path: Path):
    """Fügt eine Atempause nach dem Satz hinzu"""
    if not BREATH_WAV.exists():
        return
    try:
        merged = path.with_name(f"{path.stem}_breath.wav")
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", f"concat:{path}|{BREATH_WAV}",
            "-acodec", "copy", str(merged)
        ], check=True)
        path.unlink(missing_ok=True)
        merged.rename(path)
        print("💨 Breath hinzugefügt.")
    except Exception:
        pass

# ============================================================
# 🎧 Hauptgenerierung
# ============================================================
def generate_tts(sentence: str) -> Path | None:
    sentence = sanitize_text(sentence)
    path = wav_path(sentence)
    if path.exists():
        return path
    raw = SOUNDS_MAIN / f"tts_raw_{path.stem}.wav"
    try:
        if TTS_ENGINE == "xttsv2":
            tts_model.tts_to_file(
                text=sentence,
                file_path=str(raw),
                speaker_wav=REFERENCE_WAV if os.path.exists(REFERENCE_WAV) else None,
                language=LANG
            )
        else:
            tts_model.tts_to_file(text=sentence, file_path=str(raw))
        convert_to_asterisk(raw, path)
        add_breath_after(path)
    except Exception as e:
        print(f"❌ Fehler bei Satz-TTS: {e}")
        return None
    return path

# ============================================================
# 🔁 Parallele Generierung
# ============================================================
def generate_next(sentence: str):
    """Hintergrund-Generierung des nächsten Satzes während der aktuelle gesprochen wird"""
    threading.Thread(target=generate_tts, args=(sentence,), daemon=True).start()

# ============================================================
# 🧩 Hauptfunktion
# ============================================================
def tts_to_media(text: str) -> str | None:
    try:
        text = sanitize_text(text)
        if not text:
            return None
        print(f"🎙️ Generiere TTS (Engine={TTS_ENGINE.upper()})…")

        sentences = split_sentences(text)
        if not sentences:
            sentences = [text]

        for i, s in enumerate(sentences):
            path = generate_tts(s)
            if path:
                print(f"💾 Satz gespeichert: {path}")
            # Parallel nächste generieren, falls vorhanden
            if i + 1 < len(sentences):
                generate_next(sentences[i + 1])
            # kleine Pause zwischen Sätzen für Natürlichkeit
            time.sleep(0.25)

        last_hash = hashlib.md5(sentences[-1].encode()).hexdigest()
        return f"sound:aiagent/tts_{last_hash}"

    except Exception as e:
        print(f"❌ TTS Fehler: {e}")
        return None

