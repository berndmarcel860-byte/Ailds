#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
🎧 Atemgeräusch Generator – Einzelversion (breath1.wav)
============================================================
Erzeugt ein natürlich klingendes Atemgeräusch für XTTSv2.
Eigenschaften:
- Realistisches Einatmen (leichtes, warmes Rauschen)
- 8 kHz, Mono, PCM16 (Asterisk-kompatibel)
- Keine Abhängigkeiten außer numpy & soundfile
============================================================
"""

import numpy as np
import soundfile as sf
from pathlib import Path

OUT_DIR = Path("/var/lib/asterisk/sounds/aiagent")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_breath(output: Path, duration=0.45, volume=0.018):
    """
    Erzeugt ein leises Einatmen (Breath-In)
    """
    sr = 8000  # Asterisk-kompatibel
    t = np.linspace(0, duration, int(sr * duration))
    
    # Grundrauschen (braunes Rauschen für weichen Klang)
    breath = np.random.normal(0, 1, len(t))
    envelope = np.exp(-5 * t)  # Laut am Anfang, leiser am Ende
    breath *= envelope
    breath += 0.004 * np.sin(2 * np.pi * 60 * t)  # leichte Tieftonmodulation
    breath = breath / np.max(np.abs(breath)) * volume

    # Sanftes Fade-In und Fade-Out
    fade_len = int(sr * 0.05)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)
    breath[:fade_len] *= fade_in
    breath[-fade_len:] *= fade_out

    sf.write(str(output), breath, sr)
    print(f"✅ {output.name} erzeugt ({duration}s, vol={volume})")

if __name__ == "__main__":
    output = OUT_DIR / "breath1.wav"
    generate_breath(output)
    print(f"✅ Fertig! Datei gespeichert unter: {output}")
