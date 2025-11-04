# -*- coding: utf-8 -*-
"""
============================================================
🤖 Role Manager for AI Outbound Agent
Lädt Rollendefinitionen aus Umgebungsvariablen und Dateien (2025)
============================================================
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class RoleManager:
    def __init__(self):
        self.role = os.getenv("ROLE", "invest").lower()
        self._load_role_config()
        
    def _load_role_config(self):
        """Lädt die Rollenkonfiguration basierend auf ROLE Umgebungsvariable"""
        if self.role == "recover":
            self.agent_name = os.getenv("RECOVER_AGENT_NAME", "KryptoXPay Agent")
            self.company = os.getenv("RECOVER_AGENT_COMPANY", "KryptoXPay")
            self.role_file_path = os.getenv("ROLE_PATH_RECOVER", "./roles/role_fund_recovery.txt")
            self.agent_type = "Fund Recovery"
        else:
            self.agent_name = os.getenv("INVEST_AGENT_NAME", "Neo")
            self.company = os.getenv("INVEST_AGENT_COMPANY", "Next Quantum")
            self.role_file_path = os.getenv("ROLE_PATH_INVEST", "./roles/role_investment.txt")
            self.agent_type = "Investment"
        
        # Lade die detaillierte Rollendefinition
        self.role_definition = self._load_role_definition()
        
    def _load_role_definition(self):
        """Lädt die vollständige Rollendefinition aus der Text-Datei"""
        try:
            role_file = Path(self.role_file_path)
            if role_file.exists():
                with open(role_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                print(f"✅ Rollendefinition geladen: {self.role_file_path}")
                return content
            else:
                print(f"⚠️ Rollendatei nicht gefunden: {self.role_file_path}")
                return self._create_fallback_definition()
        except Exception as e:
            print(f"⚠️ Fehler beim Laden der Rollendatei: {e}")
            return self._create_fallback_definition()
    
    def _create_fallback_definition(self):
        """Erstellt eine Fallback-Rollendefinition"""
        if self.role == "recover":
            return f"""# Rollendefinition - {self.agent_type}
Name: {self.agent_name}
Company: {self.company}
Tone: professionell, empathisch

Mission: Du hilfst Menschen, Gelder von betrügerischen Plattformen zurückzufordern.
Du analysierst SEPA- und Blockchain-Transaktionen mit KI-Algorithmen.
Ziel: Unverbindliche Termine für Erstprüfungen vereinbaren.
"""
        else:
            return f"""# Rollendefinition - {self.agent_type}
Name: {self.agent_name}
Company: {self.company}  
Tone: professionell, überzeugend

Mission: Du zeigst Anlegern KI-gestützte Investmentstrategien.
Ziel: Interesse wecken und Informationsmaterial anbieten.
"""
    
    def get_system_prompt(self):
        """Gibt den system prompt für das LLM zurück"""
        return self.role_definition
    
    def get_agent_info(self):
        """Gibt Agent-Informationen zurück"""
        return {
            "name": self.agent_name,
            "company": self.company,
            "role": self.role,
            "type": self.agent_type,
            "role_file": self.role_file_path
        }
    
    def __str__(self):
        info = self.get_agent_info()
        return f"🤖 {info['name']} - {info['company']} ({info['type']})"

# Globale Instanz
role_manager = RoleManager()