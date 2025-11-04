# -*- coding: utf-8 -*-
"""
============================================================
🤖 GPT Logic v4 – Stable Dynamic Role Support (OpenAI)
============================================================
- Dynamische Rollenunterstützung (Investment / Recovery)
- system_prompt aus main.py integriert
- Volle Unterstützung deutscher Umlaute (ä, ö, ü, ß)
- GPT-4o-mini optimiert mit Timeout-Handling
- Intent-Erkennung integriert (detect_intent)
============================================================
"""

import os, re, random, traceback, time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from openai import OpenAI, APIError, RateLimitError, AuthenticationError

# ============================================================
# 🔐 Setup
# ============================================================
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

if not API_KEY or not API_KEY.startswith("sk-"):
    print("⚠️ Kein gültiger OpenAI API-Key gefunden – GPT deaktiviert.")
    client = None
else:
    try:
        client = OpenAI(api_key=API_KEY)
    except Exception as e:
        print(f"❌ Fehler beim Initialisieren des OpenAI-Clients: {e}")
        client = None

# ============================================================
# 🧩 Gesprächsstatus
# ============================================================
STATES = {
    "explained_ai": False,
    "appointment_set": False,
    "terminated": False
}

# ============================================================
# 🔍 Intent-Erkennung
# ============================================================
def detect_intent(text: str) -> str:
    """Erkennt grobe Gesprächsabsicht anhand von Schlüsselwörtern."""
    if not text:
        return "EMPTY"

    t = text.lower()
    if any(w in t for w in [
        "kein interesse", "nicht interessiert", "nein danke",
        "tschüss", "auf wiedersehen", "ciao", "bye"
    ]):
        return "CLOSE"

    if any(w in t for w in [
        "termin", "berater", "vereinbaren", "rückruf",
        "anruf", "gespräch", "kontakt", "information"
    ]):
        return "APPOINTMENT"

    if any(w in t for w in [
        "ja", "okay", "gut", "passt", "einverstanden", "klar"
    ]):
        return "AGREE"

    return "OTHER"

# ============================================================
# 🧠 Basis-Prompt
# ============================================================
BASE_PROMPT = """
Du bist ein professioneller deutschsprachiger KI-Gesprächsagent.
Deine genaue Rolle (Investment, Fund-Recovery, Beratung usw.) wird über einen Leitfaden geladen.
Wenn kein Leitfaden aktiv ist:
- Sprich ruhig, professionell und vertrauenswürdig.
- Verwende echte deutsche Umlaute (ä, ö, ü, ß).
- Formuliere vollständige, flüssige Sätze.
- Sei empathisch, aber zielorientiert.
"""

AI_EXPLANATION = (
    "Unsere KI-Systeme analysieren Märkte, Zinsbewegungen und historische Trends, "
    "um Chancen frühzeitig zu erkennen. Damit lassen sich stabile, planbare Erträge erzielen, "
    "ohne hohe Risiken einzugehen. Wäre das für Sie interessant?"
)

FOLLOWUP_VARIANTS = [
    "Unsere KI arbeitet vollständig automatisiert und überwacht Märkte in Echtzeit.",
    "Viele Investoren waren überrascht, wie präzise die Ergebnisse sind.",
    "Wir verbinden künstliche Intelligenz mit bewährten Strategien für planbare Renditen.",
    "Unsere Beratung ist transparent, seriös und unverbindlich.",
    "Der Ansatz wurde mehrfach unabhängig geprüft und zertifiziert."
]

FAREWELL_TEXT = "Alles klar, ich wünsche Ihnen einen angenehmen Tag und auf Wiederhören!"

# ============================================================
# 🧹 Textaufbereitung
# ============================================================
def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = s.replace("..", ".").replace("...", "…")
    s = s.replace('"', '„').replace("'", "’")
    if not s.endswith((".", "!", "?")):
        s += "."
    return s

# ============================================================
# ⚙️ Sicherer GPT-Call
# ============================================================
def safe_gpt_call(system_prompt: str, prompt: str, timeout_sec: int = 8) -> str:
    """ GPT-Abfrage mit Timeout, Retry und Fallback """
    if not client:
        return "Unsere KI erkennt Chancen automatisch. Wäre das für Sie interessant?"

    def _call():
        return client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.65,
            max_tokens=400,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

    for attempt in range(3):
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_call)
                result = future.result(timeout=timeout_sec)
            text = result.choices[0].message.content.strip()
            return clean_text(text)

        except FutureTimeout:
            print(f"⚠️ GPT Timeout ({timeout_sec}s) – Versuch {attempt+1}/3")
        except AuthenticationError:
            print("❌ Ungültiger OpenAI-API-Key – bitte neuen Key setzen.")
            return "Ich habe momentan keinen Zugriff auf das KI-System."
        except (APIError, RateLimitError) as e:
            print(f"⚠️ API Error: {e} – Retry {attempt+1}/3")
        except Exception as e:
            print(f"❌ GPT Fehler: {e}")
            print(traceback.format_exc())

        time.sleep(1.0)

    return "Entschuldigung, ich habe Sie nicht ganz verstanden."

# ============================================================
# 🧠 Hauptlogik mit Rollensteuerung
# ============================================================
def gpt_response(state: dict, user_text: str, system_prompt: str | None = None) -> str:
    """ Generiert eine KI-Antwort unter Berücksichtigung des Gesprächszustands """
    try:
        hist = state.get("history", [])
        explained_ai = state.get("explained_ai", False)
        appointment_set = state.get("appointment_set", False)
        terminated = state.get("terminated", False)

        if terminated:
            return FAREWELL_TEXT

        # Dynamische Rolle / Fallback
        active_prompt = system_prompt if system_prompt else BASE_PROMPT

        # Kontextsteuerung
        if not explained_ai:
            active_prompt += "\nWenn der Kunde zustimmt, erkläre kurz und verständlich, wie die KI funktioniert."
        elif not appointment_set:
            active_prompt += "\nLeite den Kunden freundlich zu Interesse oder Terminvereinbarung über."
        else:
            active_prompt += "\nWenn der Termin vereinbart wurde, verabschiede dich professionell."

        # Gesprächsverlauf
        context = "\n".join([
            f"{'Agent' if m['role']=='assistant' else 'Kunde'}: {m['content']}"
            for m in hist[-6:]
        ])

        prompt = f"""
Bisheriges Gespräch:
{context}

Kunde: {user_text}

Antworte professionell, ruhig und empathisch.
Sprich in natürlichem Deutsch mit echten Umlauten (ä, ö, ü, ß).
Antworte in vollständigen, flüssigen Sätzen ohne Wiederholungen.
"""

        # "Ja"-Antwort → Feste KI-Erklärung
        if not explained_ai and user_text.lower().strip() in ["ja", "stimmt", "genau", "richtig", "ja bitte"]:
            state["explained_ai"] = True
            return AI_EXPLANATION

        # GPT Antwort generieren
        resp = safe_gpt_call(active_prompt, prompt, timeout_sec=7)
        if not resp:
            print("⚠️ GPT lieferte keine Antwort – Fallback verwendet.")
            resp = random.choice(FOLLOWUP_VARIANTS)

        # Zustände aktualisieren
        if any(k in resp.lower() for k in ["algorithmus", "analyse", "ki", "strategie"]):
            state["explained_ai"] = True
        if any(k in resp.lower() for k in ["termin", "berater", "vereinbaren", "gespräch"]):
            state["appointment_set"] = True
        if any(k in user_text.lower() for k in ["tschüss", "auf wiedersehen", "ciao", "bye"]):
            state["terminated"] = True

        # Wiederholungsschutz
        if len(hist) >= 2 and resp == hist[-1]["content"]:
            resp = random.choice(FOLLOWUP_VARIANTS)
        if random.random() < 0.25:
            resp += " " + random.choice(FOLLOWUP_VARIANTS)

        return clean_text(resp)

    except Exception as e:
        print("❌ GPT Logic Error:", e)
        print(traceback.format_exc())
        return "Entschuldigung, ich habe Sie nicht ganz verstanden. Können Sie das bitte wiederholen?"

