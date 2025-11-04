# -*- coding: utf-8 -*-
"""
============================================================
🤖 AI Outbound Agent v8 – .env Integrated + Streaming
============================================================
- Nutzt alle Werte aus deiner .env-Datei
- Satzweise Streaming (parallel TTS-Generierung)
- Aufnahme erst nach letztem Agent-Satz
- Breath-Option mit einer WAV-Datei
- GPU Whisper (int8_float16) + XTTSv2 Voice Cloning
============================================================
"""

import os, re, json, time, datetime, warnings, traceback, pymysql, threading, queue, requests, random
from dotenv import load_dotenv
from websocket import create_connection
from pathlib import Path
from urllib.parse import quote_plus
from faster_whisper import WhisperModel
from tts_engine import tts_to_media
from gpt_logic_openai_v4_1 import gpt_response, detect_intent

# ============================================================
# 🌍 Environment
# ============================================================
load_dotenv()
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PYTHONWARNINGS"] = "ignore"

def ts(): return datetime.datetime.now().strftime("%H:%M:%S")

# ============================================================
# ⚙️ Konfiguration aus .env
# ============================================================
ARI_HOST = os.getenv("ARI_HOST", "127.0.0.1")
ARI_PORT = int(os.getenv("ARI_PORT", "8088"))
ARI_USER = os.getenv("ARI_USER", "ai_agent")
ARI_PASS = os.getenv("ARI_PASS", "ai_agent_secure_password_123")
APP      = os.getenv("ARI_APP", "aiagent")

ROLE     = os.getenv("ROLE", "recover").lower()

if ROLE == "recover":
    AGENT_NAME = os.getenv("RECOVER_AGENT_NAME", "Fund Recovery Agent")
    COMPANY    = os.getenv("RECOVER_AGENT_COMPANY", "FundRecovery GmbH")
    ROLE_FILE  = os.getenv("ROLE_PATH_RECOVER", "./roles/role_fund_recovery.txt")
else:
    AGENT_NAME = os.getenv("INVEST_AGENT_NAME", "Neo")
    COMPANY    = os.getenv("INVEST_AGENT_COMPANY", "Next Quantum")
    ROLE_FILE  = os.getenv("ROLE_PATH_INVEST", "./roles/role_investment.txt")

LANGUAGE = os.getenv("LANGUAGE", "de")

ASTERISK_SOUNDS_DIR = Path(os.getenv("ASTERISK_SOUNDS_DIR", "/var/lib/asterisk/sounds"))
RECORD_DIR = Path(os.getenv("ASTERISK_RECORDINGS_DIR", "/var/spool/asterisk/recording"))
RECORD_DIR.mkdir(parents=True, exist_ok=True)
SOUNDS_MAIN = ASTERISK_SOUNDS_DIR / "aiagent"
SOUNDS_MAIN.mkdir(parents=True, exist_ok=True)

TTS_SENTENCE_PAUSE = float(os.getenv("TTS_SENTENCE_PAUSE", "0.25"))
MAX_RECORDING_DURATION = int(os.getenv("MAX_RECORDING_DURATION", "12"))
MAX_SILENCE_SEC = int(os.getenv("MAX_SILENCE_SEC", "2"))

# BREATH_WAV removed - SSML breaks not used
# BREATH_ENABLED removed - natural pauses via programmatic delays

# ============================================================
# 🧠 Whisper (GPU)
# ============================================================
print("🧠 Lade Whisper STT …")
try:
    asr = WhisperModel(
        os.getenv("WHISPER_MODEL", "small"),
        device=os.getenv("WHISPER_DEVICE", "cuda"),
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8_float16")
    )
    print("✅ Whisper erfolgreich auf GPU geladen.")
except Exception as e:
    print(f"⚠️ Whisper GPU fehlgeschlagen ({e}) → CPU-Fallback.")
    asr = WhisperModel("small", device="cpu", compute_type="int8")

# ============================================================
# 💾 DB
# ============================================================
def db():
    try:
        return pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "aiagent"),
            password=os.getenv("DB_PASS", "AiAgent990"),
            database=os.getenv("DB_NAME", "ai_calls"),
            port=int(os.getenv("DB_PORT", "3306")),
            autocommit=True,
            charset="utf8mb4"
        )
    except Exception as e:
        print("DB Error:", e)
        return None

def save_turn(cid, side, text):
    try:
        conn = db()
        if not conn: return
        cur = conn.cursor()
        cur.execute("INSERT INTO turns(conversation_id, side, text, created_at) VALUES(%s,%s,%s,NOW())",
                    (cid, side, text))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print("DB save_turn:", e)

# ============================================================
# ☎️ ARI Session
# ============================================================
sess = requests.Session()
sess.auth = (ARI_USER, ARI_PASS)
STATE, ws = {}, None

def play(ch, media):
    if not media: return
    sess.post(f"http://{ARI_HOST}:{ARI_PORT}/ari/channels/{ch}/play", params={"media": media})
    while True:
        try:
            ev = json.loads(ws.recv())
            if ev.get("type") in ("PlaybackFinished", "PlaybackStopped", "ChannelHangupRequest", "StasisEnd"):
                break
        except: break

def record_start(ch):
    name = f"rec_{ch}_{int(time.time()*1000)}"
    sess.post(f"http://{ARI_HOST}:{ARI_PORT}/ari/channels/{ch}/record", params={
        "name": name,
        "format": "wav",
        "maxDurationSeconds": MAX_RECORDING_DURATION,
        "maxSilenceSeconds": MAX_SILENCE_SEC,
        "ifExists": "overwrite",
        "beep": "false"
    })
    print(f"{ts()} 🎙️ Aufnahme gestartet: {name}.wav")
    return name

def hangup(ch):
    try:
        sess.delete(f"http://{ARI_HOST}:{ARI_PORT}/ari/channels/{ch}", timeout=2)
        print(f"{ts()} 📞 Gespräch beendet: {ch}")
    except: pass

# ============================================================
# 🔊 Streaming Speech
# ============================================================
def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])', text) if s.strip()]

def speak_streamed(ch, text, cid=None):
    sentences = split_sentences(text)
    if not sentences: return
    q = queue.Queue()
    stop = threading.Event()

    def prepare():
        for s in sentences:
            if stop.is_set(): break
            media = tts_to_media(s)
            q.put(("s", s, media))
            # if BREATH_ENABLED and random.random() < 0.4:  # Breath feature removed
            # Natural pauses now handled via delays between sentences
                # q.put(("b", None, f"sound:aiagent/{Path(BREATH_WAV).stem}"))  # Removed

    threading.Thread(target=prepare, daemon=True).start()

    while True:
        try:
            typ, s, media = q.get(timeout=60)
        except queue.Empty:
            break

        if typ == "s":
            print(f"{ts()} >>> {AGENT_NAME}: {s}")
            play(ch, media)
            if cid: save_turn(cid, "AGENT", s)
            time.sleep(TTS_SENTENCE_PAUSE)
        elif typ == "b":
            play(ch, media)
            time.sleep(0.05)

        if q.empty():
            break

    stop.set()
    record_start(ch)

# ============================================================
# 📞 Gesprächslogik
# ============================================================
def greeting():
    if ROLE == "recover":
        return (
            "Hallo, mein Name ist Alex. Ich bin ein virtueller Agent basierend auf künstlicher Intelligenz "
            "von KryptoXPay, einem von der FCA lizenzierten Unternehmen, das Menschen hilft, "
            "die bei Betrugsplattformen Geld verloren haben. "
            "Darf ich Sie fragen: Haben Sie auch in der Vergangenheit Geld bei betrügerischen "
            "Investitionsplattformen verloren, wie zum Beispiel Forex, Krypto, Dating, Lotto oder Casinos?"
        )
    else:
        return (
            "Guten Tag, mein Name ist Neo von Next Quantum. "
            "Wir sprechen mit Anlegern, die an planbaren monatlichen Renditen interessiert sind. "
            "Sind Sie grundsätzlich offen für KI-gestützte Strategien?"
        )

def handle_start(ev):
    ch = ev["channel"]["id"]
    caller = ev["channel"]["caller"]["number"]
    print(f"{ts()} [📞] Neuer Anruf {ch} von {caller}")
    STATE[ch] = {"history": []}
    greet = greeting()
    speak_streamed(ch, greet)
    STATE[ch]["history"].append({"role": "assistant", "content": greet})

def handle_recording(ev):
    name = ev.get("recording", {}).get("name")
    tgt  = ev.get("recording", {}).get("target_uri", "")
    if not name or not tgt.startswith("channel:"): return
    ch = tgt.split(":", 1)[1]
    state = STATE.get(ch)
    if not state: return

    tmp = Path(f"/tmp/{name}.wav")
    text = ""
    try:
        r = sess.get(f"http://{ARI_HOST}:{ARI_PORT}/ari/recordings/stored/{quote_plus(name)}/file", stream=True)
        with open(tmp, "wb") as f:
            for c in r.iter_content(8192): f.write(c)
        segs, _ = asr.transcribe(str(tmp), language="de")
        text = " ".join(s.text for s in segs).strip()
    finally:
        tmp.unlink(missing_ok=True)

    print(f"{ts()} 💤 Kunde:", text)
    if not text:
        speak_streamed(ch, "Sind Sie noch dran?")
        return

    state["history"].append({"role": "user", "content": text})
    intent = detect_intent(text)
    if intent == "CLOSE":
        speak_streamed(ch, "Vielen Dank für das Gespräch. Auf Wiederhören!")
        hangup(ch); return

    resp = gpt_response(state, text)
    speak_streamed(ch, resp)
    state["history"].append({"role": "assistant", "content": resp})

def handle_end(ev):
    ch = ev["channel"]["id"]
    print(f"{ts()} >>> Gespräch beendet: {ch}")
    STATE.pop(ch, None)

# ============================================================
# 🚀 MAIN
# ============================================================
def main():
    global ws
    ws_url = f"ws://{ARI_HOST}:{ARI_PORT}/ari/events?api_key={ARI_USER}:{ARI_PASS}&app={APP}"
    print("="*60)
    print(f"🤖 {AGENT_NAME} – {ROLE.capitalize()} Agent aktiv")
    print(f"🏢 Firma: {COMPANY}")
    print(f"📄 Leitfaden: {ROLE_FILE}")
    print(f"🔗 Verbindung: {ws_url}")
    print("="*60)

    while True:
        try:
            ws = create_connection(ws_url)
            print(f"{ts()} ✅ Verbunden. Warte auf Anrufe…")
            while True:
                ev = json.loads(ws.recv())
                t = ev.get("type")
                if   t == "StasisStart":       handle_start(ev)
                elif t == "RecordingFinished": handle_recording(ev)
                elif t in ("StasisEnd", "ChannelHangupRequest"):
                    handle_end(ev)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("❌ Fehler:", e)
            print(traceback.format_exc())
            time.sleep(2)

if __name__ == "__main__":
    main()

