"""
Audio I/O Module for Chiku: Record and playback with Voice Activity Detection (VAD)

Features:
- Real-time audio recording with intelligent silence detection
- Voice Activity Detection using Silero VAD (lightweight, accurate)
- Automatic end-of-speech detection (no fixed timeouts)
- Audio file save/load helpers
- Cross-platform support (Windows, macOS, Linux)
"""

import numpy as np
import sounddevice as sd
from collections import deque
from pathlib import Path
import logging
from typing import Tuple, Optional, Union

try:
    import torch
    from silero_vad import load_silero_vad
except ImportError:
    raise ImportError("Please install torch and silero-vad: pip install torch silero-vad")

import config

logger = logging.getLogger(__name__)

# ============ GLOBALS ============
VAD_MODEL = None  # Lazy-loaded on first use

def resolve_device_setting(
    device_setting: Optional[Union[int, str]],
    kind: str = "input"
) -> Optional[Union[int, str]]:
    """Resolve an audio device setting from config to a valid sd device selector."""
    if device_setting is None:
        return None
    if isinstance(device_setting, str) and device_setting.isdigit():
        return int(device_setting)
    return device_setting


def get_device_info(
    device: Optional[Union[int, str]],
    kind: str = "input"
) -> Optional[dict]:
    """Return the sounddevice device info for the given kind."""
    try:
        return sd.query_devices(device, kind=kind)
    except Exception:
        return None


def initialize_vad_model():
    """Lazy load Silero VAD model on first call"""
    global VAD_MODEL
    if VAD_MODEL is None:
        logger.info("🎤 Loading Silero VAD model...")
        try:
            # Try different loading methods for compatibility
            try:
                VAD_MODEL = load_silero_vad()
            except TypeError:
                # Fallback for different API versions
                VAD_MODEL = load_silero_vad(onnx=False)
            
            # Move to GPU if available
            if torch.cuda.is_available():
                VAD_MODEL.to("cuda")
                logger.info("✅ Silero VAD loaded (device: cuda)")
            else:
                logger.info("✅ Silero VAD loaded (device: cpu)")
        except Exception as e:
            logger.error(f"❌ Failed to load VAD model: {e}")
            # Fallback: disable VAD and use timeout-based recording
            logger.warning("⚠️  VAD disabled - using timeout-based recording")
            VAD_MODEL = None
    return VAD_MODEL


# ============ RECORDING ============

def record_until_silence(
    timeout_sec: int = config.AUDIO["max_recording_duration"],
    silence_duration_ms: int = config.AUDIO["silence_duration"],
    vad_threshold: float = config.AUDIO["vad_threshold"],
    sample_rate: int = config.AUDIO["sample_rate"],
    verbose: bool = True
) -> np.ndarray:
    """
    Records audio until voice activity stops.
    
    Uses Silero VAD to detect when user stops speaking. Much better UX than fixed timeouts.
    
    Args:
        timeout_sec: Maximum recording duration (safety net)
        silence_duration_ms: How long silence = end of speech (default 500ms)
        vad_threshold: Confidence threshold for speech detection (0-1, higher = stricter)
        sample_rate: Audio sample rate (Hz)
        verbose: Print status messages
    
    Returns:
        np.ndarray: Audio array (mono, float32, sample_rate Hz)
        
    Example:
        >>> audio = record_until_silence()
        >>> print(f"Recorded {len(audio) / 16000:.1f} seconds")
    """
    
    # Initialize VAD
    vad_model = initialize_vad_model()
    
    if vad_model is None:
        # Fallback: simple timeout-based recording
        logger.warning("🎤 VAD unavailable - using 3-second timeout recording")
        return record_fixed_duration(3.0, sample_rate, verbose)
    
    vad_device = "cuda" if next(vad_model.parameters()).is_cuda else "cpu"

    input_device = resolve_device_setting(config.AUDIO.get("input_device"), kind="input")
    if verbose:
        device_info = get_device_info(input_device, kind="input")
        if device_info is not None:
            print(f"🎤 Using input device: {device_info['name']}")
        else:
            print("🎤 Using default input device")

    chunk_duration_ms = 32  # VAD expects 512 samples at 16kHz (32ms)
    chunk_samples = int(sample_rate * chunk_duration_ms / 1000)  # 512 samples
    silence_chunks_needed = int(silence_duration_ms / chunk_duration_ms)  # ~15 chunks for 500ms
    max_chunks = int(timeout_sec * 1000 / chunk_duration_ms)
    
    audio_chunks = []
    silence_counter = 0
    chunk_count = 0
    speech_started = False
    
    if verbose:
        print("🎤 Listening... speak now (will stop after silence)")
    
    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=config.AUDIO["channels"],
            dtype=config.AUDIO["dtype"],
            blocksize=chunk_samples,
            latency="low",
            device=input_device
        ) as stream:
            
            while chunk_count < max_chunks:
                # Read audio chunk
                chunk, overflowed = stream.read(chunk_samples)
                if overflowed:
                    logger.warning("⚠️  Audio buffer overflow (speech may be cut)")
                
                chunk = chunk.flatten()
                
                # Amplify audio to boost low microphone levels (much higher gain)
                chunk = chunk * 50.0  # 50x amplification for very quiet microphones
                # Prevent clipping
                chunk = np.clip(chunk, -1.0, 1.0)
                
                audio_chunks.append(chunk)
                chunk_count += 1
                
                # Run VAD on chunk
                chunk_tensor = torch.from_numpy(chunk).to(vad_device)
                confidence = vad_model(chunk_tensor, sample_rate).item()
                is_speech = confidence > vad_threshold
                
                if is_speech:
                    speech_started = True
                    silence_counter = 0
                    if verbose:
                        print(f"  [speaking] {confidence:.2f}", end="\r")
                else:
                    if speech_started:
                        silence_counter += 1
                        if verbose:
                            print(f"  [silence] {silence_counter}/{silence_chunks_needed}  ", end="\r")
                        
                        # If enough silence after speech, stop
                        if silence_counter >= silence_chunks_needed:
                            if verbose:
                                print("\n✅ Speech ended (silence detected)")
                            break
                    else:
                        # Haven't started speaking yet
                        if verbose and chunk_count % 10 == 0:
                            print(f"  [waiting...] {confidence:.2f}", end="\r")
        
        # Combine all chunks
        audio = np.concatenate(audio_chunks)
        
        # Debug: Check audio properties
        logger.debug(f"🎤 Recorded audio shape: {audio.shape}, dtype: {audio.dtype}, range: [{audio.min():.3f}, {audio.max():.3f}]")
        
        # Trim trailing silence
        audio = trim_trailing_silence(audio, sample_rate)
        
        if verbose:
            duration = len(audio) / sample_rate
            print(f"📊 Recorded {duration:.1f} seconds of audio")
        
        return audio
        
    except KeyboardInterrupt:
        print("\n⏹️  Recording stopped by user")
        audio = np.concatenate(audio_chunks) if audio_chunks else np.array([])
        return audio
    except Exception as e:
        logger.error(f"❌ Recording error: {e}")
        raise


def record_fixed_duration(
    duration_sec: float = 5.0,
    sample_rate: int = config.AUDIO["sample_rate"],
    verbose: bool = True
) -> np.ndarray:
    """
    Simple fixed-duration recording (backup option if VAD is unavailable).
    
    Args:
        duration_sec: How long to record
        sample_rate: Audio sample rate (Hz)
        verbose: Print status
    
    Returns:
        np.ndarray: Audio array
    """
    samples = int(duration_sec * sample_rate)
    
    if verbose:
        print(f"🎤 Recording for {duration_sec} seconds...")
    
    input_device = resolve_device_setting(config.AUDIO.get("input_device"), kind="input")
    if verbose:
        device_info = get_device_info(input_device, kind="input")
        if device_info is not None:
            print(f"🎤 Using input device: {device_info['name']}")
        else:
            print("🎤 Using default input device")

    try:
        audio = sd.rec(
            frames=samples,
            samplerate=sample_rate,
            channels=config.AUDIO["channels"],
            dtype=config.AUDIO["dtype"],
            latency="low",
            device=input_device
        )
        sd.wait()
        
        # Amplify audio
        audio = audio * 50.0
        # Prevent clipping
        audio = np.clip(audio, -1.0, 1.0)
        
        if verbose:
            print(f"✅ Recording complete ({duration_sec}s)")
        
        return audio.flatten()
    except Exception as e:
        logger.error(f"❌ Recording error: {e}")
        raise


# ============ PLAYBACK ============

def play_audio(
    audio: np.ndarray,
    sample_rate: int = config.AUDIO["sample_rate"],
    verbose: bool = False
) -> None:
    """
    Play audio array through speakers.
    
    Args:
        audio: Audio array (mono or stereo)
        sample_rate: Sample rate (Hz)
        verbose: Print status
        
    Example:
        >>> audio = np.sin(2 * np.pi * 440 * np.arange(16000) / 16000)
        >>> play_audio(audio)
    """
    try:
        output_device = resolve_device_setting(config.AUDIO.get("output_device"), kind="output")
        if verbose:
            print("🔊 Playing audio...")
        
        sd.play(audio, samplerate=sample_rate, device=output_device, blocking=False)
        sd.wait()
        
        if verbose:
            print("✅ Playback complete")
            
    except Exception as e:
        logger.error(f"❌ Playback error: {e}")
        raise


async def play_audio_async(
    audio: np.ndarray,
    sample_rate: int = config.AUDIO["sample_rate"],
) -> None:
    """Async wrapper for play_audio (non-blocking)"""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: play_audio(audio, sample_rate))


# ============ UTILITIES ============

def trim_trailing_silence(
    audio: np.ndarray,
    sample_rate: int = config.AUDIO["sample_rate"],
    threshold_db: float = -40
) -> np.ndarray:
    """
    Remove silence from end of audio.
    
    Args:
        audio: Audio array
        sample_rate: Sample rate
        threshold_db: Silence threshold in dB
    
    Returns:
        Audio trimmed at end
    """
    # Convert to dB
    S = np.abs(audio)
    S_db = 20 * np.log10(S + 1e-9)
    
    # Find last sample above threshold
    above_threshold = S_db > threshold_db
    if np.any(above_threshold):
        last_idx = np.where(above_threshold)[0][-1]
        return audio[:last_idx + 1]
    else:
        return audio


def trim_leading_silence(
    audio: np.ndarray,
    sample_rate: int = config.AUDIO["sample_rate"],
    threshold_db: float = -40
) -> np.ndarray:
    """Remove silence from beginning of audio."""
    S = np.abs(audio)
    S_db = 20 * np.log10(S + 1e-9)
    
    above_threshold = S_db > threshold_db
    if np.any(above_threshold):
        first_idx = np.where(above_threshold)[0][0]
        return audio[first_idx:]
    else:
        return audio


def trim_silence(audio: np.ndarray, sample_rate: int = config.AUDIO["sample_rate"]) -> np.ndarray:
    """Remove silence from both ends"""
    audio = trim_leading_silence(audio, sample_rate)
    audio = trim_trailing_silence(audio, sample_rate)
    return audio


def save_audio(
    audio: np.ndarray,
    filepath: str,
    sample_rate: int = config.AUDIO["sample_rate"]
) -> None:
    """
    Save audio array to WAV file (useful for debugging).
    
    Args:
        audio: Audio array
        filepath: Output file path
        sample_rate: Sample rate
    """
    import scipy.io.wavfile as wavfile
    
    # Convert float32 to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    
    wavfile.write(filepath, sample_rate, audio_int16)
    logger.info(f"💾 Saved audio to {filepath}")


def load_audio(
    filepath: str,
    sample_rate: int = config.AUDIO["sample_rate"],
    mono: bool = True
) -> np.ndarray:
    """
    Load audio from file.
    
    Args:
        filepath: Audio file path
        sample_rate: Resample to this rate (if different from file)
        mono: Convert to mono
        
    Returns:
        Audio array as float32
    """
    try:
        import librosa
    except ImportError as e:
        raise ImportError(
            "librosa is required to load audio files. Install it with: pip install librosa"
        ) from e

    # Load with librosa for flexibility
    audio, sr = librosa.load(filepath, sr=sample_rate, mono=mono)
    return audio.astype(np.float32)


def get_audio_duration(audio: np.ndarray, sample_rate: int = config.AUDIO["sample_rate"]) -> float:
    """Get audio duration in seconds"""
    return len(audio) / sample_rate


def test_audio_devices() -> None:
    """Diagnostic: List available audio devices"""
    print("\n🔊 Available Audio Devices:")
    print(sd.query_devices())
    print(f"\nDefault input: {sd.default.device[0]}")
    print(f"Default output: {sd.default.device[1]}")


if __name__ == "__main__":
    # Test recording
    print("Testing audio I/O...\n")
    
    test_audio_devices()
    
    audio = record_until_silence(timeout_sec=10, verbose=True)
    print(f"\nRecorded {get_audio_duration(audio):.1f} seconds")
    
    # Playback as verification
    print("\nPlaying back in 2 seconds...")
    import time
    time.sleep(2)
    play_audio(audio, verbose=True)
