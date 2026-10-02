# Chiku - Personal Voice Assistant MVP 1

> A real-time, dynamic AI voice assistant inspired by Jarvis from Marvel's Iron Man.

## 🚀 Quick Start

```bash
# 1. Clone and install dependencies
cd chiku-assistant
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Start Ollama (in a separate terminal)
ollama serve

# 3. Pull the Mistral model
ollama pull mistral:7b

# 4. Run FastAPI server (in another terminal)
python server.py

# 5. Run CLI client (in another terminal)
python client.py --voice
```

---

## 📋 Features (MVP 1)

✅ **Real-time voice capture** with intelligent Voice Activity Detection (VAD)  
✅ **Speech-to-text** using OpenAI Whisper (base.en model)  
✅ **AI conversation** powered by Mistral 7B via Ollama  
✅ **Natural speech synthesis** with XTTS-v2 TTS  
✅ **Multi-turn conversations** with persistent memory  
✅ **Jarvis-like personality** - professional, witty, responsive  
✅ **WebSocket API** for real-time communication  
✅ **Session management** - save and restore conversations  

---

## 🛠️ System Architecture

```
┌─────────────────────────────────────┐
│  Client Layer                       │
│  ├─ CLI Interactive Interface       │
│  ├─ WebSocket Connection            │
│  └─ Audio I/O (sounddevice)         │
└──────────┬──────────────────────────┘
           │
┌──────────▼──────────────────────────┐
│  Server Layer (FastAPI)             │
│  ├─ /health - Health check          │
│  ├─ /chat/{session_id} - Text API   │
│  └─ /voice/{session_id} - Voice WS  │
└──────────┬──────────────────────────┘
           │
┌──────────▼──────────────────────────┐
│  Processing Pipeline                │
│  ├─ ASR (Whisper)                   │
│  ├─ LLM (Ollama + Mistral)          │
│  ├─ TTS (XTTS-v2)                   │
│  └─ Memory (JSON sessions)          │
└─────────────────────────────────────┘
```

---

## 📦 Dependencies

### Core
- **FastAPI**: Web framework for WebSocket server
- **Uvicorn**: ASGI server
- **Websockets**: WebSocket protocol support

### AI Models
- **Whisper**: Speech recognition (OpenAI)
- **Ollama**: Local LLM inference server
- **TTS**: Text-to-speech (Coqui/XTTS-v2)

### Audio
- **sounddevice**: Cross-platform audio I/O
- **numpy**: Numerical operations
- **scipy**: Audio processing
- **silero-vad**: Voice activity detection (lightweight)

### Optional (Phase 2)
- **resemblyzer**: Speaker verification (voice fingerprinting)

---

## 🎯 Usage Guide

### Voice Mode (Real-time conversation)

```bash
python client.py --voice
```

**What happens:**
1. "🎤 Listening..." appears
2. Speak your question (e.g., "What's the weather?")
3. System detects silence (~500ms) and stops recording
4. Whisper transcribes your speech
5. Mistral generates a response
6. XTTS-v2 synthesizes speech
7. Audio plays back through speakers
8. Repeat

**Controls:**
- Press `Ctrl+C` to exit

### Text Mode (Type input, hear responses)

```bash
python client.py --text
```

**Example:**
```
You: What's your name?
Chiku: I'm Chiku, your personal AI assistant inspired by Jarvis from Iron Man. How can I help you?

You: Tell me a joke
Chiku: Why did the AI go to school? Because it wanted to improve its learning models!
```

### Session Management

**List all conversations:**
```bash
python client.py --list-sessions
```

**Use a specific session:**
```bash
python client.py --voice --session conversation_001
```

**Test audio setup:**
```bash
python client.py --test-audio
```

**Test model availability:**
```bash
python client.py --test-models
```

---

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Audio settings
AUDIO = {
    "sample_rate": 16000,           # Hz
    "silence_duration": 500,        # ms (stop after this silence)
    "max_recording_duration": 10,   # seconds (safety limit)
    "vad_threshold": 0.5,           # VAD confidence (higher = stricter)
}

# ASR (Whisper)
ASR = {
    "model": "base.en",             # tiny.en, small.en, medium.en, large
    "device": "cuda",               # cuda / cpu
}

# LLM
LLM = {
    "backend": "ollama",          # ollama, huggingface, or openai
    "model": "mistral:7b",        # model name for the selected backend
    "api_key": "",                # OpenAI or Hugging Face API key, if needed
    "temperature": 0.7,             # Creativity
    "top_p": 0.9,
    "num_predict": 256,
    "num_ctx": 2048,
}

# TTS (XTTS-v2)
TTS = {
    "model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
    "device": "cuda",               # cuda / cpu
}
```

---

## 📚 API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00",
  "features": {...},
  "ollama": {
    "healthy": true,
    "model": "mistral:7b",
    "available_models": ["mistral:7b", "llama2:7b"]
  }
}
```

### Text Chat
```bash
curl -X POST "http://localhost:8000/chat/default?text=What%27s%20your%20name?"
```

**Response:**
```json
{
  "status": "success",
  "user_input": "What's your name?",
  "assistant_response": "I'm Chiku, your personal AI assistant.",
  "message_count": 1
}
```

### WebSocket Voice
```bash
python client.py --voice
```

**Message format:**
```json
{"type": "status", "message": "Transcribing..."}
{"type": "transcript", "text": "What's the weather?"}
{"type": "response", "text": "I don't have real-time weather data..."}
```

---

## ⚙️ Troubleshooting

### "Connection refused" (Ollama not running)
```bash
# Start Ollama in a new terminal
ollama serve

# Pull model if not already downloaded
ollama pull mistral:7b
```

### "Audio device error"
```bash
# List available audio devices
python client.py --test-audio

# If the default microphone is wrong, set the correct index or name in config.py:
#   AUDIO["input_device"] = 0
#   AUDIO["output_device"] = 1
```

### "Model taking too long to download"
First TTS run downloads ~1GB model. This can take 5-10 minutes depending on internet.

### "Transcription empty"
- Speak clearly and louder
- Check microphone levels: `python client.py --test-audio`
- Reduce `VAD_THRESHOLD` in config.py (default 0.5, try 0.3)

### "Ollama model not found"
```bash
# List available models
ollama list

# Pull missing model
ollama pull mistral:7b

# Or use a different model
# ollama pull llama2:7b
# (Then update config.py LLM model)
```

---

## 📁 Project Structure

```
chiku-assistant/
├── audio_io.py                 # Audio I/O with VAD
├── asr.py                      # Whisper ASR wrapper
├── llm.py                      # Ollama LLM client
├── tts.py                      # XTTS-v2 TTS wrapper
├── memory.py                   # Session management
├── speaker_auth.py             # Speaker verification (Phase 2)
├── server.py                   # FastAPI WebSocket server
├── client.py                   # CLI interactive client
│
├── config.py                   # Global configuration
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
│
├── integrations/
│   ├── calendar.py             # Calendar stub
│   ├── web_search.py           # Web search stub
│   └── device_control.py       # Smart home stub
│
├── conversations/              # Session JSON files (created on first run)
├── speaker_profiles/           # Voice fingerprints (Phase 2)
│
└── README.md                   # This file
```

---

## 🔍 Testing Components

### Test Audio I/O
```bash
python audio_io.py
```
Records 5 seconds of audio and plays it back.

### Test ASR (Whisper)
```bash
python asr.py
```
Requires a `test_audio.wav` file.

### Test LLM
```bash
python llm.py
```
Verifies the configured LLM backend. For `ollama` it checks local Ollama; for `huggingface` and `openai` it validates remote API reachability.

### Test TTS (XTTS-v2)
```bash
python tts.py
```
Generates "Hello, I am Chiku" and plays it back.

### Test Session Memory
```bash
python memory.py
```
Creates, saves, and loads a test conversation.

---

## 🚀 Performance

**Typical latency (end-to-end):**
- Audio capture: 1-5 seconds (user-dependent)
- ASR: ~500ms
- LLM generation: ~1-3 seconds
- TTS synthesis: ~500ms - 2 seconds
- **Total: 2-5 seconds** (acceptable for MVP)

**System Requirements:**
- **CPU Only**: Can run on any modern CPU (slow but functional)
- **GPU Recommended**: NVIDIA CUDA GPU for 2x-3x speedup

---

## 🔐 Privacy & Security

✅ **All open-source**: No proprietary APIs
✅ **Runs locally**: No data sent to external services
✅ **Conversation storage**: Local JSON files only
✅ **Speaker auth (Phase 2)**: Optional voice fingerprinting for access control

---

## 📝 Roadmap

### Phase 1: MVP ✅ (Current)
- [x] Voice-in → Text transcription
- [x] Text → AI response generation
- [x] Response → Voice-out
- [x] Multi-turn conversation memory
- [x] Voice Activity Detection for natural interaction
- [x] WebSocket real-time API

### Phase 2: Enhanced Features (3-5 days)
- [ ] Speaker verification (voice-only access)
- [ ] Calendar integration (Google/Outlook)
- [ ] Web search integration (real-time info)
- [ ] Smart home control (HomeAssistant/LIFX)
- [ ] Custom voice cloning

### Phase 3: Production (Future)
- [ ] Multi-language support
- [ ] Desktop application (Electron)
- [ ] Mobile app integration
- [ ] Advanced NLU (intent recognition)
- [ ] Skill extensibility

---

## 🤝 Contributing

This is a personal project. Feel free to fork and customize!

---

## 📄 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- **Whisper**: OpenAI's speech recognition model
- **Ollama**: Local LLM inference server
- **XTTS-v2**: Coqui's multilingual text-to-speech
- **Silero VAD**: Lightweight voice activity detection
- **Inspiration**: Tony Stark's Jarvis assistant

---

## 📞 Support

For issues, questions, or suggestions:
1. Check the **Troubleshooting** section above
2. Review log files in `conversations/` directory
3. Test individual components (`python component.py`)

---

**Happy chatting with Chiku!** 🎤🤖
