"""
FastAPI Server for Chiku: Real-time voice assistant with WebSocket support

Routes:
- GET /health - Server health check
- POST /chat/{session_id} - Text-based chat (for testing)
- WebSocket /voice/{session_id} - Real-time voice input/output
"""

import logging
import json
import math
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional
from datetime import datetime

import config
from audio_io import record_until_silence, play_audio
from asr import transcribe
from llm import generate_with_context, generate_with_context_streaming, check_health, list_available_models
import tts
from memory import get_session, list_sessions
from speaker_auth import verify_speaker
import numpy as np

# ============ LOGGING ============
logging.basicConfig(
    level=getattr(logging, config.LOGGING["level"].upper()),
    format=config.LOGGING["format"]
)
logger = logging.getLogger(__name__)

WS_AUDIO_CHUNK_SIZE = 256 * 1024  # 256KB per binary frame
WS_TEXT_CHUNK_SIZE = 12000       # chunk large text responses into smaller JSON frames


def _normalize_response_text(text: str) -> str:
    if not text:
        return text

    def _replace_action(match: re.Match) -> str:
        action = match.group(1).strip().lower()
        if re.search(r"\b(laughs|laughing|giggles|giggle|chuckles|chuckles|lol|haha|heh)\b", action):
            return " Ha ha!"
        if re.search(r"\b(sighs|sigh)\b", action):
            return " *sigh* "
        if re.search(r"\b(smiles|grins|smiles)\b", action):
            return ""
        return ""

    text = re.sub(r"\((.*?)\)", _replace_action, text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text

async def _send_json_in_chunks(websocket: WebSocket, message_type: str, text: str, **meta) -> None:
    if text is None:
        text = ""
    if len(text) <= WS_TEXT_CHUNK_SIZE:
        await websocket.send_json({"type": message_type, "text": text, **meta})
        return

    chunks = [text[i:i + WS_TEXT_CHUNK_SIZE] for i in range(0, len(text), WS_TEXT_CHUNK_SIZE)]
    total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        await websocket.send_json({
            "type": f"{message_type}_chunk",
            "text": chunk,
            "part": index,
            "total_parts": total,
            **meta
        })
    await websocket.send_json({"type": f"{message_type}_complete", "part_count": total, **meta})


async def _send_audio_chunks(websocket: WebSocket, audio_bytes: bytes, sample_rate: int) -> None:
    total_bytes = len(audio_bytes)
    chunks = math.ceil(total_bytes / WS_AUDIO_CHUNK_SIZE)
    await websocket.send_json({
        "type": "audio_start",
        "sample_rate": sample_rate,
        "byte_length": total_bytes,
        "chunks": chunks
    })
    for i in range(0, total_bytes, WS_AUDIO_CHUNK_SIZE):
        await websocket.send_bytes(audio_bytes[i:i + WS_AUDIO_CHUNK_SIZE])
    await websocket.send_json({"type": "audio_end", "chunks": chunks, "byte_length": total_bytes})

# ============ FASTAPI SETUP ============
app = FastAPI(
    title="Chiku - Personal Voice Assistant",
    description="Real-time voice assistant inspired by Real world AI companion. Powered by FastAPI, Whisper ASR, and pyttsx3 TTS.",
    version="0.1.0"
)

# CORS middleware (allow frontend connections)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ ROUTES ============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    backend_healthy = check_health()
    backend_name = config.LLM["backend"]
    
    return {
        "status": "ok" if backend_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "voice_input": config.FEATURES["voice_input"],
            "text_input": config.FEATURES["text_input"],
            "speaker_auth": config.FEATURES["speaker_auth"],
            "conversation_memory": config.FEATURES["conversation_memory"],
        },
        "llm": {
            "backend": backend_name,
            "healthy": backend_healthy,
            "model": config.LLM["model"],
            "available_models": list_available_models() if backend_name == "ollama" and backend_healthy else []
        }
    }


@app.post("/chat/{session_id}")
async def text_chat(session_id: str, text: str):
    """
    Text-based chat endpoint (for testing without voice).
    
    Args:
        session_id: Session identifier
        text: User input text
        
    Returns:
        JSON with response and session info
    """
    
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        # Get or create session
        session = get_session(session_id)
        
        # Add user message
        session.add_message("user", text)
        
        # Generate response with context
        response_text = generate_with_context(
            text,
            session.get_last_n_turns(),
            stream=False,
            verbose=False
        )
        
        # Add assistant response
        session.add_message("assistant", response_text)
        
        # Save session
        session.save()
        
        return {
            "status": "success",
            "session_id": session_id,
            "user_input": text,
            "assistant_response": response_text,
            "message_count": len(session.messages)
        }
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/voice/{session_id}")
async def websocket_voice(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time voice interaction.
    
    Protocol:
    1. Client connects
    2. Server prompts for audio (optional speaker auth)
    3. Client sends audio bytes (raw PCM)
    4. Server: transcribes → generates response → synthesizes → sends back audio
    5. Loop repeats until client disconnects
    """
    
    await websocket.accept()
    logger.info(f"🔌 WebSocket connected: {session_id}")
    
    try:
        # Get or create session
        session = get_session(session_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "message": f"Hey RAJAT! Welcome back to Chiku — your hilariously helpful AI sidekick. Session: {session_id}",
            "session_info": {
                "id": session_id,
                "message_count": len(session.messages),
                "created_at": session.created_at
            }
        })
        
        # Main voice loop
        while True:
            # Prompt for audio
            await websocket.send_json({
                "type": "ready",
                "message": "Listening... (speak now)"
            })
            
            # Receive audio data
            data = await websocket.receive_bytes()
            logger.debug(f"📥 Received {len(data)} bytes of audio")
            
            try:
                # Convert bytes to numpy array (client sends int16, convert to float32)
                audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767
                
                # Transcribe
                await websocket.send_json({
                    "type": "status",
                    "message": "Transcribing..."
                })
                
                result = await asyncio.to_thread(
                    transcribe,
                    audio_data=audio,
                    sample_rate=16000
                )
                transcript = result["text"]
                
                if not transcript:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No speech detected"
                    })
                    continue
                
                await websocket.send_json({
                    "type": "transcript",
                    "text": transcript
                })
                
                logger.info(f"📝 Transcript: {transcript}")
                
                # Add to session and generate response
                session.add_message("user", transcript)
                
                await websocket.send_json({
                    "type": "status",
                    "message": "Generating response..."
                })
                
                # Use streaming LLM for lower latency
                response_text = ""
                tts_task = None
                audio_future = None
                
                try:
                    async for chunk in generate_with_context_streaming(
                        transcript,
                        session.get_last_n_turns(),
                        stream=True,
                        verbose=False
                    ):
                        response_text += chunk
                        
                        # Start TTS synthesis when we have enough text (but not too early)
                        if len(response_text.strip()) >= 50 and tts_task is None:
                            await websocket.send_json({
                                "type": "status", 
                                "message": "Starting speech synthesis..."
                            })
                            
                            # Start TTS in background
                            async def synthesize_and_send():
                                try:
                                    normalized_text = _normalize_response_text(response_text)
                                    audio_response, sample_rate = await asyncio.to_thread(
                                        tts.synthesize,
                                        normalized_text,
                                        verbose=False
                                    )
                                    if isinstance(audio_response, np.ndarray) and audio_response.size > 0:
                                        audio_bytes = (audio_response * 32767).astype(np.int16).tobytes()
                                        await _send_audio_chunks(websocket, audio_bytes, sample_rate)
                                        logger.info(f"🔊 Sent {len(audio_bytes)} bytes of synthesized speech ({sample_rate} Hz)")
                                    else:
                                        logger.warning("🔊 TTS generated empty audio")
                                except Exception as e:
                                    logger.warning(f"🔊 TTS synthesis failed: {e}")
                            
                            tts_task = asyncio.create_task(synthesize_and_send())
                    
                    # Wait for TTS to complete if it was started
                    if tts_task:
                        await tts_task
                        
                except Exception as e:
                    logger.error(f"❌ Streaming response error: {e}")
                    # Fallback to non-streaming if streaming fails
                    response_text = await asyncio.to_thread(
                        generate_with_context,
                        transcript,
                        session.get_last_n_turns(),
                        stream=False,
                        verbose=False
                    )
                    
                    # Send response text
                    normalized_text = _normalize_response_text(response_text)
                    await _send_json_in_chunks(
                        websocket,
                        "response",
                        normalized_text
                    )
                    
                    # Synthesize and send audio
                    try:
                        await websocket.send_json({
                            "type": "status",
                            "message": "Generating speech..."
                        })
                        audio_response, sample_rate = await asyncio.to_thread(
                            tts.synthesize,
                            response_text,
                            verbose=False
                        )
                        if isinstance(audio_response, np.ndarray) and audio_response.size > 0:
                            audio_bytes = (audio_response * 32767).astype(np.int16).tobytes()
                            await _send_audio_chunks(websocket, audio_bytes, sample_rate)
                            logger.info(f"🔊 Sent {len(audio_bytes)} bytes of synthesized speech ({sample_rate} Hz)")
                        else:
                            logger.warning("🔊 TTS generated empty audio")
                    except Exception as e:
                        logger.warning(f"🔊 TTS synthesis failed: {e}")
                
                # Add assistant response to session
                normalized_text = _normalize_response_text(response_text)
                session.add_message("assistant", normalized_text)
                
                # Send final response text if not already sent
                if not tts_task:  # Only send if we didn't use streaming TTS
                    await _send_json_in_chunks(
                        websocket,
                        "response",
                        normalized_text
                    )

                # Save session
                session.save()
                
            except WebSocketDisconnect:
                logger.info(f"❌ Client disconnected during processing: {session_id}")
                break
            except Exception as e:
                logger.error(f"❌ Processing error: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Error: {str(e)}"
                    })
                except WebSocketDisconnect:
                    logger.info(f"❌ Could not send error message, client disconnected: {session_id}")
                    break
    
    except WebSocketDisconnect:
        logger.info(f"❌ WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Server error: {str(e)}"
        })


@app.get("/sessions")
async def get_sessions_list():
    """List all conversation sessions"""
    sessions = list_sessions()
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get info about a specific session"""
    session = get_session(session_id)
    return {
        "session_id": session_id,
        "created_at": session.created_at,
        "last_updated": session.last_updated,
        "message_count": len(session.messages),
        "messages": session.get_last_n_turns(n=10)  # Last 10 messages
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    from memory import _session_manager
    _session_manager.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


# ============ STARTUP/SHUTDOWN ============

@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    logger.info("🚀 Chiku starting up...")
    
    backend_name = config.LLM["backend"]
    if check_health():
        if backend_name == "ollama":
            models = list_available_models()
            logger.info(f"✅ Ollama ready with models: {models}")
        else:
            logger.info(f"✅ {backend_name} backend is reachable")
    else:
        logger.warning(f"⚠️  {backend_name} backend not responding. Voice features may not work.")
    
    logger.info("✅ Chiku startup complete")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("👋 Chiku shutting down...")
    # Save all sessions
    from memory import _session_manager
    _session_manager.save_all()
    logger.info("✅ All sessions saved")


# ============ MAIN ============

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🌐 Starting server on {config.SERVER['host']}:{config.SERVER['port']}")
    
    uvicorn.run(
        app,
        host=config.SERVER["host"],
        port=config.SERVER["port"],
        log_level=config.SERVER["log_level"],
        reload=False,  # Disable reload for direct script execution
        ws_ping_interval=config.WEBSOCKET["ping_interval"],
        ws_ping_timeout=config.WEBSOCKET["ping_timeout"],
    )
