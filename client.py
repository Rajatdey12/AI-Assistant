"""
Chiku CLI Client: Interactive voice assistant interface

Features:
- Real-time voice recording (with VAD silence detection)
- WebSocket connection to Chiku server
- Audio playback of responses
- Multi-turn conversation with memory
- Session management
"""

import asyncio
import websockets
import json
import numpy as np
import logging
from pathlib import Path
from typing import Optional
import argparse
import sys

import config
from audio_io import (
    record_until_silence,
    record_fixed_duration,
    play_audio,
    play_audio_async,
    get_audio_duration,
    test_audio_devices
)
from memory import get_session, list_sessions
import asr
import llm
import tts

# ============ LOGGING ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============ CLIENT CLASS ============

class ChikuClient:
    """Interactive client for Chiku voice assistant"""
    
    def __init__(self, server_url: str = "ws://localhost:8000", session_id: str = "default"):
        """
        Initialize client.
        
        Args:
            server_url: WebSocket server URL
            session_id: Conversation session ID
        """
        self.server_url = server_url
        self.session_id = session_id
        self.websocket = None
        self.running = False
        self.response_event = asyncio.Event()
        self.last_audio_sample_rate = 22050
        self._pending_audio_bytes = bytearray()
        self._receiving_audio = False
        self._pending_response_chunks = []
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            full_url = f"{self.server_url}/voice/{self.session_id}"
            logger.info(f"🔌 Connecting to {full_url}...")
            self.websocket = await websockets.connect(
                full_url,
                ping_interval=config.WEBSOCKET["ping_interval"],
                ping_timeout=config.WEBSOCKET["ping_timeout"],
                close_timeout=config.WEBSOCKET["close_timeout"],
            )
            logger.info("✅ Connected")
            
            # Receive welcome message
            msg = await self.websocket.recv()
            data = json.loads(msg)
            print(f"\n{data.get('message', 'Connected')}\n")
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            logger.info("👋 Disconnected")
    
    async def send_audio(self, audio: np.ndarray) -> None:
        """Send audio to server"""
        audio_bytes = (audio * 32767).astype(np.int16).tobytes()
        await self.websocket.send(audio_bytes)
        logger.debug(f"📤 Sent {len(audio_bytes)} bytes")
    
    async def receive_messages(self) -> None:
        """Receive and handle messages from server"""
        try:
            while self.running:
                msg = await self.websocket.recv()

                if isinstance(msg, bytes):
                    if self._receiving_audio:
                        self._pending_audio_bytes.extend(msg)
                        logger.debug(f"🔊 Received audio chunk ({len(msg)} bytes)")
                    else:
                        logger.warning("⚠️ Received unexpected binary frame")
                else:
                    data = json.loads(msg)
                    await self._handle_json_message(data)

        except asyncio.CancelledError:
            logger.info("🔌 Message receiver cancelled")
            raise
        except websockets.exceptions.ConnectionClosedOK:
            logger.info("🔌 WebSocket connection closed normally")
            self.running = False
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"❌ WebSocket connection closed with error: {e}")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Receive error: {e}")
            self.running = False
    
    async def _handle_json_message(self, data: dict) -> None:
        """Handle JSON messages from server"""
        msg_type = data.get("type", "unknown")
        message = data.get("message", "")
        
        if msg_type == "status":
            print(f"  ℹ️  {message}")
        elif msg_type == "transcript":
            text = data.get("text", "")
            print(f"  💬 You: {text}")
        elif msg_type == "response":
            text = data.get("text", "")
            print(f"  🤖 Chiku: {text}\n")
            self.response_event.set()
        elif msg_type == "response_chunk":
            self._pending_response_chunks.append(data.get("text", ""))
        elif msg_type == "response_complete":
            full_text = "".join(self._pending_response_chunks)
            self._pending_response_chunks.clear()
            print(f"  🤖 Chiku: {full_text}\n")
            self.response_event.set()
        elif msg_type == "audio_start":
            self._receiving_audio = True
            self._pending_audio_bytes = bytearray()
            self.last_audio_sample_rate = data.get("sample_rate", self.last_audio_sample_rate)
            print(f"  🔊 Receiving audio response ({data.get('chunks', 1)} chunks)")
        elif msg_type == "audio_end":
            self._receiving_audio = False
            if self._pending_audio_bytes:
                audio = np.frombuffer(self._pending_audio_bytes, dtype=np.int16).astype(np.float32) / 32767
                await play_audio_async(audio, sample_rate=self.last_audio_sample_rate)
                self._pending_audio_bytes = bytearray()
            else:
                logger.warning("⚠️ Audio end received with no audio data")
            self.response_event.set()
        elif msg_type == "audio":
            self.last_audio_sample_rate = data.get("sample_rate", self.last_audio_sample_rate)
            print(f"  🔊 Audio response ready ({self.last_audio_sample_rate} Hz)")
        elif msg_type == "audio_error":
            print(f"  ❌ Voice output failed: {data.get('message', 'Unknown error')}\n")
            self.response_event.set()
        elif msg_type == "error":
            print(f"  ❌ Error: {message}")
            self.response_event.set()
        elif msg_type == "ready":
            print(f"  {message}")
        elif msg_type == "welcome":
            pass  # Already printed
    
    async def voice_loop(self) -> None:
        """Main voice interaction loop"""
        self.running = True
        receiver_task = asyncio.create_task(self.receive_messages())

        try:
            while self.running:
                # Record audio with VAD
                try:
                    print("\n🎤 Recording (speak now, will stop after silence)...")
                    audio = record_until_silence(
                        timeout_sec=config.AUDIO["max_recording_duration"],
                        silence_duration_ms=config.AUDIO["silence_duration"],
                        verbose=True
                    )

                    duration = get_audio_duration(audio)
                    print(f"  ✅ Recorded {duration:.1f} seconds")

                    if duration < 0.1 or audio.size == 0:
                        print("  ❌ No audio captured, please try again.")
                        continue
                except KeyboardInterrupt:
                    print("\n⏹️  Recording cancelled")
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"❌ Recording failure: {e}")
                    continue

                # Send to server
                print("  📤 Sending...")
                await self.send_audio(audio)

                # Wait for response event from server
                print("  ⏳ Waiting for response...")
                try:
                    await asyncio.wait_for(
                        self.response_event.wait(),
                        timeout=config.LLM["request_timeout"] + 10
                    )
                except asyncio.TimeoutError:
                    print(f"  ⚠️ No response received within {config.LLM['request_timeout'] + 10} seconds.")
                finally:
                    self.response_event.clear()

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Voice loop error: {e}")
            self.running = False
        finally:
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass
    
    async def text_loop(self) -> None:
        """Text-based chat loop (for testing)"""
        self.running = True
        import requests
        
        base_url = self.server_url.replace("ws", "http").replace("/voice/", "/")
        
        try:
            while self.running:
                print()
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "bye"]:
                    break
                
                # Send to server
                try:
                    response = requests.post(
                        f"{base_url}chat/{self.session_id}",
                        params={"text": user_input},
                        timeout=10
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    chiku_response = result.get("assistant_response", "")
                    print(f"Chiku: {chiku_response}\n")
                
                except Exception as e:
                    logger.error(f"❌ Request error: {e}")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            logger.error(f"❌ Text loop error: {e}")
    
    async def run_voice(self) -> None:
        """Run voice interaction"""
        try:
            await self.connect()
            await self.voice_loop()
        finally:
            await self.disconnect()
    
    def run_text(self) -> None:
        """Run text interaction (sync)"""
        try:
            asyncio.run(self.connect())
            asyncio.run(self.text_loop())
        finally:
            asyncio.run(self.disconnect())


# ============ CLI INTERFACE ============

def print_banner():
    """Print welcome banner"""
    print("""
╔════════════════════════════════════════════════╗
║           🎤 CHIKU - Voice Assistant 🎤        ║
║        Inspired by Jarvis from Iron Man        ║
╚════════════════════════════════════════════════╝
    """)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Chiku - Personal Voice Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Voice mode (real-time voice I/O)
  python client.py --voice
  
  # Text mode (type questions, Chiku responds with voice)
  python client.py --text
  
  # Connect to remote server
  python client.py --voice --server ws://remote-ip:8000
  
  # List sessions
  python client.py --list-sessions
  
  # Test audio devices
  python client.py --test-audio
        """
    )
    
    parser.add_argument("--voice", action="store_true", help="Voice mode (default)")
    parser.add_argument("--text", action="store_true", help="Text mode (type input)")
    parser.add_argument("--server", default="ws://localhost:8000", help="Server WebSocket URL")
    parser.add_argument("--session", default="default", help="Session ID")
    parser.add_argument("--list-sessions", action="store_true", help="List all sessions")
    parser.add_argument("--test-audio", action="store_true", help="Test audio devices")
    parser.add_argument("--test-models", action="store_true", help="Test model availability")
    
    args = parser.parse_args()
    
    print_banner()
    
    # Handle special commands
    if args.test_audio:
        test_audio_devices()
        return
    
    if args.test_models:
        print("\n🧪 Testing Model Availability...\n")
        
        print("📢 TTS Model:")
        try:
            info = tts.get_model_info()
            print(f"  ✅ {info['model']}")
        except Exception as e:
            print(f"  ❌ {e}")
        
        print("\n🎙️  ASR Model:")
        try:
            info = asr.get_model_info()
            print(f"  ✅ {info['model']}")
        except Exception as e:
            print(f"  ❌ {e}")
        
        print("\n🤖 LLM Backend:")
        try:
            backend = llm.BACKEND
            if llm.check_health():
                print(f"  ✅ {backend} backend is reachable")
                if backend == "ollama":
                    models = llm.list_available_models()
                    print(f"     Available models: {models}")
            else:
                print(f"  ❌ {backend} backend not responding")
                if backend == "ollama":
                    print(f"     Start with: ollama serve")
        except Exception as e:
            print(f"  ❌ {e}")
        
        return
    
    if args.list_sessions:
        sessions = list_sessions()
        print("\n📋 Conversation Sessions:")
        if sessions:
            for sid in sessions:
                s = get_session(sid)
                print(f"  - {sid}: {len(s.messages)} messages, updated {s.last_updated}")
        else:
            print("  (None)")
        return
    
    # Connect to server
    client = ChikuClient(server_url=args.server, session_id=args.session)
    
    print(f"\n📍 Session: {args.session}")
    print(f"🌐 Server: {args.server}\n")
    
    # Determine mode
    use_voice = args.voice or (not args.text)
    
    if use_voice:
        print("🎤 Voice Mode")
        print("   - Speak clearly")
        print("   - Chiku responds with speech (Press Ctrl+C to exit)\n")
        
        try:
            asyncio.run(client.run_voice())
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
    else:
        print("💬 Text Mode")
        print("   - Type your questions")
        print("   - Chiku responds with voice (Type 'exit' to quit)\n")
        
        try:
            client.run_text()
        except Exception as e:
            logger.error(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
