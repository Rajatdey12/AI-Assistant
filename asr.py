"""
ASR (Automatic Speech Recognition) Module for Chiku: Google Speech Recognition

Features:
- Google Speech API integration (accurate, free tier)
- Simple and reliable
- Language support
- Confidence scoring
"""

import speech_recognition as sr
import numpy as np
import logging
from typing import Dict, Optional
from pathlib import Path
import config

logger = logging.getLogger(__name__)

# ============ GLOBALS ============
RECOGNIZER = sr.Recognizer()

def transcribe(audio_data: np.ndarray, sample_rate: int = 16000) -> Dict[str, any]:
    """
    Transcribe audio data using Google Speech Recognition.

    Args:
        audio_data: Numpy array of audio samples (16kHz, mono)
        sample_rate: Sample rate (should be 16000)

    Returns:
        Dict with 'text', 'confidence', 'language' keys
    """
    try:
        # Debug: Check audio properties
        logger.debug(f"🎙️  Audio shape: {audio_data.shape}, dtype: {audio_data.dtype}, range: [{audio_data.min():.3f}, {audio_data.max():.3f}]")

        # Convert float32 audio to int16 for Google Speech API
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio = sr.AudioData(audio_int16.tobytes(), sample_rate, 2)  # 2 bytes per sample for int16

        # Recognize speech directly from the provided audio buffer
        result = RECOGNIZER.recognize_google(audio, show_all=True)

        if result:
            # Get the most confident result
            best_result = max(result['alternative'], key=lambda x: x.get('confidence', 0))
            text = best_result['transcript']
            confidence = best_result.get('confidence', 0.8)  # Default if not provided

            logger.info(f"🎙️  Transcribed: '{text}' (confidence: {confidence:.2f})")
            return {
                "text": text,
                "confidence": confidence,
                "language": "en-US"  # Google default
            }
        else:
            logger.warning("🎙️  No speech detected")
            return {"text": "", "confidence": 0.0, "language": "en-US"}

    except sr.UnknownValueError:
        logger.warning("🎙️  Could not understand audio")
        return {"text": "", "confidence": 0.0, "language": "en-US"}
    except sr.RequestError as e:
        logger.error(f"🎙️  Google Speech API error: {e}")
        return {"text": "", "confidence": 0.0, "language": "en-US"}
    except Exception as e:
        logger.error(f"🎙️  ASR error: {e}")
        return {"text": "", "confidence": 0.0, "language": "en-US"}

def initialize_model():
    """
    Initialize the speech recognizer (no-op for Google API).
    """
    logger.info("🎙️  Google Speech Recognition initialized")
    return RECOGNIZER


def transcribe_whisper(
    audio_path: Optional[str] = None,
    audio_array: Optional[np.ndarray] = None,
    language: str = config.ASR["language"],
    verbose: bool = True
) -> Dict:
    """
    Transcribe audio using Whisper.
    
    Args:
        audio_path: Path to audio file (mp3, wav, m4a, etc.)
        audio_array: NumPy audio array (float32, 16kHz)
        language: Language code (e.g., 'en', 'es', 'fr')
        verbose: Print progress
    
    Returns:
        Dict with keys:
        - 'text': Transcribed text
        - 'language': Detected language
        - 'confidence': Confidence score (0-1, if available)
        - 'segments': List of segment dicts (timing info)
    
    Examples:
        >>> result = transcribe_whisper("audio.wav")
        >>> print(result['text'])
        
        >>> import numpy as np
        >>> audio = np.random.randn(16000)  # 1 second
        >>> result = transcribe_whisper(audio_array=audio)
    """
    
    model = initialize_whisper_model()
    
    try:
        if audio_path is not None:
            if verbose:
                print(f"📝 Transcribing {audio_path}...")
            
            result = model.transcribe(
                audio=audio_path,
                language=language,
                fp16=config.ASR.get("fp16", True),
                verbose=verbose
            )
            
        elif audio_array is not None:
            if verbose:
                duration = len(audio_array) / config.AUDIO["sample_rate"]
                print(f"📝 Transcribing {duration:.1f}s audio...")
            
            # Whisper expects sample rate of 16kHz
            if len(audio_array.shape) > 1:
                audio_array = audio_array.flatten()
            
            result = model.transcribe(
                audio=audio_array,
                language=language,
                fp16=config.ASR.get("fp16", True),
                verbose=verbose
            )
        else:
            raise ValueError("Must provide audio_path or audio_array")
        
        # Extract key info
        transcript = result.get("text", "").strip()
        detected_language = result.get("language", language)
        
        if verbose:
            print(f"✅ Transcription: {transcript[:100]}...")
        
        return {
            "text": transcript,
            "language": detected_language,
            "segments": result.get("segments", []),
            "full_result": result  # Store full result for inspection
        }
        
    except Exception as e:
        logger.error(f"❌ Transcription error: {e}")
        raise


def transcribe_batch(
    audio_paths: list,
    language: str = config.ASR["language"]
) -> list:
    """
    Transcribe multiple audio files.
    
    Args:
        audio_paths: List of file paths
        language: Language code
    
    Returns:
        List of result dicts
    """
    results = []
    for i, path in enumerate(audio_paths):
        print(f"[{i+1}/{len(audio_paths)}] Processing {path}...")
        result = transcribe_whisper(audio_path=path, language=language, verbose=False)
        results.append(result)
    return results


def get_model_info() -> Dict:
    """Get info about loaded Whisper model"""
    model = initialize_whisper_model()
    return {
        "model": config.ASR["model"],
        "encoder_params": sum(p.numel() for p in model.encoder.parameters()),
        "decoder_params": sum(p.numel() for p in model.decoder.parameters()),
        "device": next(model.parameters()).device,
    }


if __name__ == "__main__":
    # Test transcription
    print("Testing Whisper ASR...\n")
    
    # Generate test audio (1 second silence + 1 second sine wave)
    import config
    sr = config.AUDIO["sample_rate"]
    
    # Real example: use a recorded audio file if available
    test_file = Path("test_audio.wav")
    
    if test_file.exists():
        result = transcribe_whisper(str(test_file))
        print(f"\n📝 Transcribed text: {result['text']}")
        print(f"🗣️  Language: {result['language']}")
    else:
        print("❓ No test audio file found.")
        print("   Run audio_io.py first to record test audio, then try again.")
