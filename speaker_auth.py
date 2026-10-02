"""
Speaker Authentication Module for Chiku: Voice-only access (Phase 2 optional)

Features:
- Voice fingerprinting using Resemblyzer
- Speaker enrollment (create voice profile)
- Speaker verification (authenticate incoming voice)
- Similarity scoring
"""

import numpy as np
import json
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict
import config

logger = logging.getLogger(__name__)

try:
    from resemblyzer import VoiceEncoder, preprocess_wav
except ImportError:
    logger.warning("⚠️  resemblyzer not installed. Speaker auth disabled.")
    VoiceEncoder = None


# ============ GLOBALS ============
ENCODER = None  # Lazy-loaded on first use

def initialize_encoder():
    """Lazy load voice encoder"""
    global ENCODER
    if ENCODER is None and VoiceEncoder is not None:
        logger.info("🎙️  Loading voice encoder (Resemblyzer)...")
        try:
            ENCODER = VoiceEncoder()
            logger.info("✅ Voice encoder loaded")
        except Exception as e:
            logger.error(f"❌ Failed to load encoder: {e}")
            raise
    return ENCODER


def enroll_speaker(
    audio_path: str,
    user_id: str = "default_user",
    overwrite: bool = False
) -> Dict:
    """
    Enroll a speaker (create voice profile).
    
    Args:
        audio_path: Path to 3-5 second audio sample of speaker's voice
        user_id: Unique identifier for this speaker
        overwrite: Whether to overwrite existing profile
    
    Returns:
        Dict with enrollment info
        
    Example:
        >>> result = enroll_speaker("my_voice.wav", user_id="rajat")
        >>> print(f"Enrolled: {result['user_id']}")
    """
    
    if not config.SPEAKER_AUTH["enabled"]:
        logger.warning("⚠️  Speaker auth disabled in config")
        return {"status": "disabled"}
    
    encoder = initialize_encoder()
    if encoder is None:
        logger.error("❌ Voice encoder not available")
        raise RuntimeError("Resemblyzer not installed")
    
    # Check file
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Check existing profile
    profile_path = config.SPEAKER_PROFILES_DIR / f"{user_id}_embedding.json"
    if profile_path.exists() and not overwrite:
        logger.warning(f"⚠️  Profile already exists for {user_id}")
        return {"status": "exists", "user_id": user_id}
    
    try:
        # Process audio
        logger.info(f"🎤 Processing enrollment audio: {audio_path}")
        wav = preprocess_wav(str(audio_path))
        
        # Extract embedding
        embedding = encoder.embed_utterance(wav)
        
        # Save profile
        profile_data = {
            "user_id": user_id,
            "embedding": embedding.tolist(),  # Convert to list for JSON
            "audio_path": str(audio_path),
            "enrolled_at": str(np.datetime64("now")),
        }
        
        profile_path.write_text(json.dumps(profile_data, indent=2))
        
        logger.info(f"✅ Speaker {user_id} enrolled ({profile_path})")
        
        return {
            "status": "enrolled",
            "user_id": user_id,
            "embedding_dim": len(embedding),
        }
        
    except Exception as e:
        logger.error(f"❌ Enrollment failed: {e}")
        raise


def verify_speaker(
    audio_path: str,
    user_id: str = "default_user",
    threshold: Optional[float] = None
) -> Tuple[bool, float]:
    """
    Verify if audio matches enrolled speaker.
    
    Args:
        audio_path: Path to test audio
        user_id: Speaker to verify against
        threshold: Similarity threshold (default from config)
    
    Returns:
        Tuple of (is_verified: bool, similarity_score: float)
        
    Example:
        >>> is_match, score = verify_speaker("test_audio.wav", user_id="rajat")
        >>> if is_match:
        ...     print(f"Verified! Similarity: {score:.2f}")
    """
    
    if not config.SPEAKER_AUTH["enabled"]:
        return True, 1.0  # Disabled, allow all
    
    encoder = initialize_encoder()
    if encoder is None:
        logger.warning("⚠️  Voice encoder not available, allowing access")
        return True, 1.0
    
    if threshold is None:
        threshold = config.SPEAKER_AUTH["similarity_threshold"]
    
    # Load profile
    profile_path = config.SPEAKER_PROFILES_DIR / f"{user_id}_embedding.json"
    if not profile_path.exists():
        logger.error(f"❌ No profile found for {user_id}")
        return False, 0.0
    
    try:
        # Load enrolled embedding
        profile_data = json.loads(profile_path.read_text())
        enrolled_embedding = np.array(profile_data["embedding"])
        
        # Process test audio
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")
        
        wav = preprocess_wav(str(audio_path))
        test_embedding = encoder.embed_utterance(wav)
        
        # Compute cosine similarity
        similarity = np.dot(enrolled_embedding, test_embedding) / (
            np.linalg.norm(enrolled_embedding) * np.linalg.norm(test_embedding)
        )
        
        is_verified = similarity > threshold
        
        status = "✅ VERIFIED" if is_verified else "❌ NOT VERIFIED"
        logger.info(f"{status}: {user_id} (score: {similarity:.3f}, threshold: {threshold})")
        
        return is_verified, float(similarity)
        
    except Exception as e:
        logger.error(f"❌ Verification error: {e}")
        return False, 0.0


def list_enrolled_speakers() -> Dict[str, str]:
    """List all enrolled speakers"""
    speakers = {}
    for profile in config.SPEAKER_PROFILES_DIR.glob("*_embedding.json"):
        user_id = profile.stem.replace("_embedding", "")
        speakers[user_id] = str(profile)
    return speakers


def delete_speaker_profile(user_id: str) -> bool:
    """Delete a speaker's profile"""
    profile_path = config.SPEAKER_PROFILES_DIR / f"{user_id}_embedding.json"
    if profile_path.exists():
        profile_path.unlink()
        logger.info(f"🗑️  Deleted profile for {user_id}")
        return True
    return False


if __name__ == "__main__":
    # Test speaker auth
    print("Testing Speaker Authentication...\n")
    
    if not config.SPEAKER_AUTH["enabled"]:
        print("⚠️  Speaker auth is DISABLED in config")
        print("   Set SPEAKER_AUTH_ENABLED=true in .env to enable\n")
    
    # Check available speakers
    speakers = list_enrolled_speakers()
    print(f"Enrolled speakers: {speakers if speakers else 'None'}\n")
    
    print("To enroll a speaker:")
    print("  result = enroll_speaker('audio_sample.wav', user_id='your_name')\n")
    
    print("To verify a speaker:")
    print("  is_match, score = verify_speaker('test_audio.wav', user_id='your_name')")
