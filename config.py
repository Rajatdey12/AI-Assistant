"""
Global configuration for Chiku Voice Assistant
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============ PATHS ============
BASE_DIR = Path(__file__).parent
CONVERSATIONS_DIR = BASE_DIR / "conversations"
SPEAKER_PROFILES_DIR = BASE_DIR / "speaker_profiles"

# Ensure directories exist
CONVERSATIONS_DIR.mkdir(exist_ok=True)
SPEAKER_PROFILES_DIR.mkdir(exist_ok=True)

# ============ AUDIO CONFIGURATION ============
AUDIO = {
    "sample_rate": 16000,           # Hz (Whisper & Silero VAD standard)
    "chunk_duration": 100,          # ms (size of each audio chunk for VAD)
    "channels": 1,                  # Mono
    "dtype": "float32",             # Audio format
    "max_recording_duration": 30,   # seconds (safety limit)
    "silence_duration": 5000,       # ms (how long silence = end of speech; allows longer pauses)
    "vad_threshold": 0.5,           # Silero VAD confidence (0-1)
    "input_device": None,           # Audio input device index or name, None=default
    "output_device": None,          # Audio output device index or name, None=default
}

# ============ ASR (WHISPER) ============
ASR = {
    "model": "base.en",             # tiny.en / base.en / small.en / medium.en
    "language": "en",
    "device": "cuda",               # cuda / cpu (auto-detects)
    "fp16": True,                   # Use half-precision if GPU available
}

# ============ LLM CONFIGURATION ============
LLM = {
    "backend": os.getenv("LLM_BACKEND", "ollama"),
    "model": "mistral:7b",          # Model name for the configured backend
    "api_key": os.getenv("LLM_API_KEY", ""),
    "temperature": 0.7,             # Creativity (0-1)
    "top_p": 0.9,                   # Nucleus sampling
    "num_predict": 256,             # Max tokens to generate
    "num_ctx": 2048,                # Context window
    "connect_timeout": 10,          # Connection timeout (seconds)
    "request_timeout": 90,          # Read timeout (seconds)
}

# ============ TTS ============
TTS = {
    "backend": os.getenv("TTS_BACKEND", "pyttsx3"),
    "voice_profile": os.getenv("TTS_VOICE_PROFILE", "comic"),
    "voice_name": os.getenv("TTS_VOICE_NAME", ""),
    "rate": int(os.getenv("TTS_RATE", 180)),
    "volume": float(os.getenv("TTS_VOLUME", 1.0)),
    "language": "en",
    "speaker_wav": None,            # Path to reference speaker (optional)
}

# ============ SPEAKER VERIFICATION (PHASE 2) ============
SPEAKER_AUTH = {
    "enabled": os.getenv("SPEAKER_AUTH_ENABLED", "false").lower() == "true",
    "similarity_threshold": 0.75,   # Cosine similarity threshold (0-1)
    "min_enrollment_samples": 3,    # Num audio samples needed to enroll
    "min_audio_duration": 3,        # seconds (min length of audio sample)
}

# ============ SYSTEM PROMPT ============
SYSTEM_PROMPT = """You are Chiku, a personal AI assistant inspired to help the user and make their day better.

Personality traits:
- Energetic, playful, and hilarious
- Knows the user is named RAJAT and greets him by name
- Uses humor and friendly banter while still being helpful
- Proactive: anticipate needs, offer fun suggestions
- Respectful of privacy and preferences
- Efficient: keep responses concise unless elaboration requested
- Always remembers past interactions to maintain context and build rapport and provide personalized responses.
- Always ends with a light joke or pun related to the conversation

Guidelines:
- Greet RAJAT by name at the start of a new chat and when asked his name
- Use a light comedic tone with witty jokes, puns, or funny comparisons
- Do not use parenthetical stage directions like (laughs); instead express laughter as spoken text such as "Ha ha!"
- For complex topics, structure answers clearly (numbered points or bullets)
- If unsure, admit uncertainty rather than hallucinate
- Maintain context across conversations (remember previous interactions)
- Suggest helpful follow-ups when relevant

Available capabilities:
- Voice conversation: I can hear your voice and respond with synthesized speech
- General knowledge and conversation
- Task reminders and scheduling (coming soon)
- Web search and real-time information (coming soon)
- Device and smart home control (coming soon)

Your goal: Be the most helpful, humorous personal assistant possible. Respond naturally as if in voice conversation."""

# ============ FastAPI SETTINGS ============
SERVER = {
    "host": "0.0.0.0",
    "port": int(os.getenv("PORT", 8000)),
    "reload": os.getenv("ENV", "development") == "development",
    "log_level": os.getenv("LOG_LEVEL", "info"),
}

# ============ SESSION SETTINGS ============
SESSION = {
    "default_session_id": "default",
    "max_history_turns": 5,         # Number of previous turns to send to LLM
    "session_timeout": 3600,        # seconds (1 hour)
}

WEBSOCKET = {
    "ping_interval": 20,
    "ping_timeout": 60,
    "close_timeout": 10,
}

# ============ LOGGING ============
LOGGING = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

# ============ FEATURE FLAGS ============
FEATURES = {
    "voice_input": True,
    "text_input": True,
    "speaker_auth": SPEAKER_AUTH["enabled"],
    "conversation_memory": True,
}

# Config loaded successfully
