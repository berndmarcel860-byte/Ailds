# AI Call-Center Agent (Ailds)

Professional German AI outbound calling agent for lead generation with support for investment and fund recovery roles.

## Features

- 🗣️ **Professional TTS**: Coqui TTS with Thorsten (German) or XTTSv2 voice cloning
- 🎧 **Speech Recognition**: Faster Whisper for accurate German transcription
- 🤖 **Conversational AI**: OpenAI GPT-4o-mini powered conversations
- 🎭 **Role Management**: Switch between investment and fund recovery personas
- 📞 **Asterisk Integration**: Full ARI (Asterisk REST Interface) support
- 🇩🇪 **Native German**: Optimized for professional German conversations

## Recent Improvements (Professional Speech)

The system has been enhanced for more professional, human-realistic outbound calls:

### ✅ SSML Removal
- Removed all SSML `<break>` tags and breath features
- Natural pauses now handled with programmatic delays (`time.sleep()`)
- No artificial SSML-based pauses in speech output

### ✅ Text Sanitization
- New `sanitizeForTTS()` utility function
- Removes punctuation (`.`, `!`, `?`) for smoother speech flow
- Collapses multiple spaces and trims whitespace
- Produces more natural, flowing speech without artificial pauses

### ✅ Voice Configuration
- `TTS_VOICE` environment variable for easy voice switching
- Default: `thorsten` (professional German male voice)
- Alternative: `xttsv2` (voice cloning with custom reference)

### ✅ Professional Speech Settings
- `TTS_RATE`: Conservative speech rate (default: 0.98)
- `TTS_PITCH`: Slight pitch downshift for authority (default: 0.95)
- `TTS_SENTENCE_PAUSE`: Natural pauses between sentences (default: 0.5s)

## Environment Variables

### TTS Configuration

```bash
# Select TTS voice
TTS_VOICE=thorsten              # thorsten | xttsv2

# Professional speech settings
TTS_RATE=0.98                   # Speech rate (0.5-1.5)
TTS_PITCH=0.95                  # Pitch adjustment (0.5-1.5)
TTS_SENTENCE_PAUSE=0.5          # Natural pause between sentences (seconds)
```

### Role Selection

```bash
# Select agent role
ROLE=recover                    # recover | invest

# Role-specific settings
RECOVER_AGENT_NAME=KryptoXPay Agent
RECOVER_AGENT_COMPANY=KryptoXPay

INVEST_AGENT_NAME=Neo
INVEST_AGENT_COMPANY=Next Quantum
```

### OpenAI Configuration

```bash
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini
```

## Setup

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings:
   - OpenAI API key
   - Asterisk ARI credentials
   - Database credentials
   - TTS voice preference

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the agent:
   ```bash
   python mainollama.py
   ```

## Text Sanitization

All text sent to the TTS engine is automatically sanitized using `sanitizeForTTS()`:

```python
from tts_engine import sanitizeForTTS

# Example
text = "Guten Tag! Wie geht es Ihnen?"
sanitized = sanitizeForTTS(text)
# Result: "Guten Tag Wie geht es Ihnen"
```

This produces more natural, professional speech without artificial pauses from punctuation.

## Role Definitions

Role behaviors are defined in text files:
- `roles/role_fund_recovery.txt` - Fund recovery agent (KryptoXPay)
- `roles/role_investment.txt` - Investment agent (Next Quantum)

Both roles are optimized for:
- Professional, empathetic conversation
- German language (formal "Sie" form)
- Lead generation for callbacks
- No pressure tactics

## Architecture

```
mainollama.py          # Main application entry point
├── gpt_logic_openai_v4_1.py   # Conversation logic with GPT
├── tts_engine.py              # Text-to-speech with sanitization
├── role_manager.py            # Role configuration management
├── telephony.py               # Asterisk ARI interface
└── generate_breath.py         # (Deprecated - breath features removed)
```

## Professional Speech Pipeline

1. **GPT Response Generation**: Natural German conversation
2. **Text Sanitization**: Remove punctuation, normalize whitespace
3. **Sentence Splitting**: Split on natural boundaries
4. **TTS Synthesis**: Generate clean audio (Thorsten or XTTSv2)
5. **Programmatic Pauses**: Natural delays between sentences
6. **Asterisk Playback**: 8kHz PCM WAV for telephony

## Configuration Examples

### Professional Investment Calls
```bash
TTS_VOICE=thorsten
TTS_RATE=0.98
TTS_PITCH=0.95
ROLE=invest
TTS_SENTENCE_PAUSE=0.5
```

### Fund Recovery Calls
```bash
TTS_VOICE=thorsten
TTS_RATE=0.98
TTS_PITCH=0.95
ROLE=recover
TTS_SENTENCE_PAUSE=0.6
```

### Voice Cloning (Custom Voice)
```bash
TTS_VOICE=xttsv2
REFERENCE_WAV=/path/to/voice/sample.wav
TTS_RATE=0.98
TTS_PITCH=0.95
```

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact the development team.
