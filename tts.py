"""
TTS (Text-to-Speech) Module for Chiku: offline voice synthesis with pyttsx3

Features:
- Offline text-to-speech via pyttsx3
- Generates WAV audio and sends binary PCM audio over WebSocket
- Falls back to clear error reporting when synthesis fails
"""

import logging
import os
import tempfile
from typing import Optional, Tuple

import numpy as np
from scipy.io.wavfile import read as wav_read

import config

logger = logging.getLogger(__name__)

TTS_AVAILABLE = False
TTS_BACKEND = None

try:
    import pyttsx3
    TTS_AVAILABLE = True
    TTS_BACKEND = "pyttsx3"
except ImportError:
    logger.warning("📢 pyttsx3 not installed - offline TTS disabled")


def _load_wav_file(filepath: str) -> Tuple[np.ndarray, int]:
    sample_rate, data = wav_read(filepath)
    if data.ndim > 1:
        data = data.mean(axis=1)

    if data.dtype == np.int16:
        audio = data.astype(np.float32) / 32767.0
    elif data.dtype == np.int32:
        audio = data.astype(np.float32) / 2147483648.0
    else:
        audio = data.astype(np.float32)
        max_val = np.abs(audio).max()
        if max_val > 1.0:
            audio = audio / max_val

    return audio, sample_rate


def _select_pyttsx3_voice(engine) -> Optional[str]:
    target_name = config.TTS.get("voice_name", "").lower()
    profile = config.TTS.get("voice_profile", "comic").lower()

    voices = engine.getProperty("voices") or []
    if target_name:
        for voice in voices:
            if target_name in voice.name.lower() or target_name in voice.id.lower():
                return voice.id

    if profile == "comic":
        preferred = ["zira", "samantha", "alloy", "emma", "karen", "michael", "david"]
        for name in preferred:
            for voice in voices:
                if name in voice.name.lower() or name in voice.id.lower():
                    return voice.id

    if profile == "human":
        for voice in voices:
            vname = voice.name.lower()
            if "english" in vname or "default" in vname:
                return voice.id

    return voices[0].id if voices else None


def _synthesize_pyttsx3(text: str) -> Tuple[np.ndarray, int]:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        engine = pyttsx3.init()
        voice_id = _select_pyttsx3_voice(engine)
        if voice_id:
            engine.setProperty("voice", voice_id)

        rate = int(config.TTS.get("rate", 180))
        volume = float(config.TTS.get("volume", 1.0))
        engine.setProperty("rate", rate)
        engine.setProperty("volume", max(0.0, min(volume, 1.0)))

        engine.save_to_file(text, temp_path)
        engine.runAndWait()

        audio, sample_rate = _load_wav_file(temp_path)
        return audio, sample_rate
    except Exception as e:
        logger.error(f"❌ pyttsx3 synthesis error: {e}")
        raise
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


def synthesize(text: str, language: str = "en", verbose: bool = True) -> Tuple[np.ndarray, int]:
    """
    Synthesize text to speech.

    Args:
        text: Text to synthesize
        language: Language code (ignored for pyttsx3)
        verbose: Print progress

    Returns:
        Tuple containing audio array and sample rate
    """
    if not text or len(text.strip()) == 0:
        return np.array([], dtype=np.float32), 22050

    if not TTS_AVAILABLE:
        raise RuntimeError("No TTS backend is available")

    if verbose:
        logger.info(f"🔊 Synthesizing speech using {TTS_BACKEND}...")

    if TTS_BACKEND == "pyttsx3":
        return _synthesize_pyttsx3(text)

    raise RuntimeError("Unsupported TTS backend")


def get_model_info() -> dict:
    """Get info about the active TTS backend."""
    return {
        "engine": TTS_BACKEND or "none",
        "available": TTS_AVAILABLE,
        "backend": TTS_BACKEND,
    }


def get_available_languages() -> list:
    """Get list of supported languages."""
    if TTS_BACKEND == "pyttsx3":
        return ["en"]
    return []


def test_voice_generation(
    text: str = "Hello, I am Chiku, your personal AI assistant.",
    save_path: Optional[str] = None
) -> np.ndarray:
    """
    Test voice generation with optional save.

    Args:
        text: Text to synthesize
        save_path: Optional path to save WAV file

    Returns:
        Audio array
    """
    audio, sample_rate = synthesize(text, verbose=True)

    if save_path and len(audio) > 0:
        from audio_io import save_audio
        save_audio(audio, save_path, sample_rate=sample_rate)
        print(f"💾 Saved to {save_path}")

    return audio
