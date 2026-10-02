# Chiku Setup Guide - Step-by-Step Installation

Follow these instructions to set up Chiku on your system.

## ✅ Prerequisites

- **OS**: Windows, macOS, or Linux
- **Python**: 3.9 or higher
- **RAM**: 8GB+ (4GB minimum for CPU-only mode)
- **Disk**: 10GB free space (for models, especially TTS)
- **GPU** (optional): NVIDIA CUDA GPU recommended for 2-3x speedup

## 📋 Step-by-Step Installation

### Step 1: Install Ollama

Ollama runs the local LLM (Mistral 7B) that powers Chiku's responses.

**Windows / macOS / Linux:**
1. Visit https://ollama.ai
2. Click "Download"
3. Install and run Ollama
4. Leave it running in the background

**Verify Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

Should return JSON with available models.

### Step 2: Pull the Mistral Model

In a terminal/PowerShell:

```bash
ollama pull mistral:7b
```

This downloads ~4GB. First time takes 5-15 minutes depending on your internet.

**Verify model is ready:**
```bash
ollama list
```

Should show `mistral:7b` in the list.

### Step 3: Clone/Download Chiku

```bash
cd ~/projects  # Or wherever you want to store it
git clone <repo_url>  # If using git
# OR download ZIP and extract

cd chiku-assistant
```

### Step 4: Create Python Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal now.

### Step 5: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- FastAPI + Uvicorn (web server)
- Whisper (speech recognition)
- TTS (text-to-speech) - ~1GB download on first run
- Silero VAD (voice activity detection)
- Other dependencies

**Note:** First pip install takes 10-20 minutes due to model downloads. Grab a coffee!

### Step 6: Create Environment Configuration

```bash
cp .env.example .env
```

Review `.env` and adjust if needed:
```
OLLAMA_BASE_URL=http://localhost:11434
SPEAKER_AUTH_ENABLED=false  # Enable in Phase 2
```

### Step 7: Verify Installation

Test all components:

```bash
# Test audio devices
python client.py --test-audio

# Test model availability
python client.py --test-models

# List audio devices (for troubleshooting)
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Expected output:
```
✅ TTS Model: tts_models/multilingual/multi-dataset/xtts_v2
✅ ASR Model: base.en
✅ LLM (Ollama): mistral:7b available
```

---

## 🚀 Running Chiku

You'll need **3 terminal windows** (or use tabs):

### Terminal 1: FastAPI Server
```bash
cd chiku-assistant
source venv/bin/activate  # Activate venv if not already
python server.py
```

Expected output:
```
🚀 Starting server on 0.0.0.0:8000
🌐 Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Terminal 2: Ollama (if not already running in background)
```bash
ollama serve
```

### Terminal 3: Chiku Client
```bash
cd chiku-assistant
source venv/bin/activate
python client.py --voice
```

Expected output:
```
╔════════════════════════════════════════════════╗
║           🎤 CHIKU - Voice Assistant 🎤       ║
║        Inspired by Real World AI companions.   ║
╚════════════════════════════════════════════════╝

📍 Session: default
🌐 Server: ws://localhost:8000

🎤 Voice Mode
   - Speak clearly
   - Chiku responds with speech (Press Ctrl+C to exit)

🎤 Listening... speak now
```

Now speak your question!

---

## 🔧 Configuration

### Audio Settings
Edit `config.py` if you want to customize:

```python
AUDIO = {
    "silence_duration": 500,     # How long silence = end of speech (ms)
    "vad_threshold": 0.5,        # VAD confidence (0-1, higher = stricter)
    "max_recording_duration": 10, # Safety limit (seconds)
}
```

### Silence Detection Tuning
If Chiku stops listening too early or too late:
- **Too early**: Increase `silence_duration` (e.g., 700ms)
- **Too late**: Decrease `silence_duration` (e.g., 300ms)

### Model Selection
Want faster responses? Use a smaller model:

```python
# In config.py
ASR["model"] = "tiny.en"  # Faster but less accurate

# For Ollama, try different models:
# ollama pull llama2:7b
# ollama pull neural-chat:7b
```

### GPU/CPU Mode
XTTS-v2 and Whisper auto-detect GPU. To force CPU:

```python
# In config.py
ASR["device"] = "cpu"
TTS["device"] = "cpu"
```

---

## 🆘 Troubleshooting

### "Cannot connect to Ollama"
- [ ] Ollama is running (`ollama serve` in another terminal)
- [ ] Ollama URL is correct in `.env` (default: `http://localhost:11434`)
- [ ] Firewall allows localhost connection
- [ ] Try: `curl http://localhost:11434/api/tags`

### "Model not found"
```bash
ollama list                # Check what's installed
ollama pull mistral:7b     # Download if missing
```

### "Audio device not found"
```bash
python:
import sounddevice as sd
print(sd.query_devices())  # List available devices
```

Then update `config.py` if needed.

### "No speech detected" / Silent recordings
- [ ] Microphone is unmuted
- [ ] Microphone volume is adequate
- [ ] Speak clearly and loud enough
- [ ] Try: `python audio_io.py` to test recording
- [ ] Increase `vad_threshold` in config.py (try 0.3 instead of 0.5)

### "TTS is very slow" (first run)
- [ ] Normal on first run (downloads ~1GB model)
- [ ] Subsequent runs are much faster (cached)
- [ ] Use CPU-only GPU for faster subsequent loads

### "Memory error" or "CUDA out of memory"
Switch to CPU mode:
```python
ASR["device"] = "cpu"
TTS["device"] = "cpu"
```

Or reduce model sizes:
```python
ASR["model"] = "tiny.en"  # Smaller model
```

### "Port 8000 already in use"
Change port in `config.py`:
```python
SERVER = {
    "port": 8001,  # Use different port
}
```

Then connect client to: `python client.py --server ws://localhost:8001`

---

## 📊 Testing Individual Components

### Test Recording
```bash
python -c "from audio_io import record_until_silence; audio = record_until_silence(); print(f'Recorded {len(audio)/16000:.1f}s')"
```

### Test Transcription
```bash
python -c "from asr import transcribe; result = transcribe('path/to/audio.wav'); print(result['text'])"
```

### Test LLM
```bash
python -c "from llm import generate; print(generate('What is your name?'))"
```

### Test TTS
```bash
python -c "from tts import synthesize; audio = synthesize('Hello world'); print(f'Generated {len(audio)} samples')"
```

### Test Full Pipeline
```bash
python client.py --test-models
```

---

## 🎯 Next Steps

1. **Run in voice mode**: `python client.py --voice`
2. **Test text mode**: `python client.py --text`
3. **Try multi-turn**: Ask follow-up questions (Chiku remembers context)
4. **Check sessions**: `python client.py --list-sessions`
5. **Review logs**: Check `conversations/` folder for saved chats

---

## 📚 Useful Commands

```bash
# List all conversations
ls conversations/

# Start fresh (delete all sessions)
rm conversations/*.json

# Test specific endpoint
curl http://localhost:8000/health

# View last 10 lines of Chiku's logs
tail -f chiku-assistant.log

# Kill Ollama process (if stuck)
pkill ollama  # macOS/Linux
taskkill /IM ollama.exe  # Windows
```

---

## ✅ Verification Checklist

Before reporting issues, verify:

- [ ] Python 3.9+ installed: `python --version`
- [ ] Virtual environment activated: `(venv)` visible in terminal
- [ ] Ollama running: `curl http://localhost:11434/api/tags` returns JSON
- [ ] Mistral model downloaded: `ollama list` shows `mistral:7b`
- [ ] Dependencies installed: `pip list | grep -i whisper` shows openai-whisper
- [ ] Audio devices detected: `python client.py --test-audio` lists devices
- [ ] Server starts: `python server.py` shows "Application startup complete"
- [ ] Client connects: `python client.py --voice` connects without errors

---

## 🆘 Still Having Issues?

1. **Check terminal output** - Read error messages carefully
2. **Check logs** - Look in `.vscode` or console output
3. **Run diagnostics** - `python client.py --test-models`
4. **Test components individually** - `python audio_io.py`, `python asr.py`, etc.
5. **Internet connection** - First run downloads large models

---

## 🎉 Success!

Once everything is working, you should be able to:
1. Speak to Chiku naturally
2. Get responses both as text and synthesized speech
3. Have context-aware multi-turn conversations
4. See all conversations persist in `conversations/` folder

Enjoy using Chiku! 🎤🤖

---

## 📝 Notes for Power Users

### Running on Headless Server
If running without display (e.g., on a server):
```bash
# Use text mode
python client.py --text

# Or disable audio playback (modify client.py)
```

### Docker Deployment
Want to containerize? Create a `Dockerfile`:
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "server.py"]
```

Then: `docker build -t chiku . && docker run -p 8000:8000 --gpus all chiku`

### Remote Connection
To access Chiku from another machine:
1. Note your machine's IP: `ipconfig` (Windows) or `ifconfig` (macOS/Linux)
2. In `.env`, set: `OLLAMA_BASE_URL=http://YOUR_IP:11434`
3. Start server: `python server.py`
4. On client machine: `python client.py --server ws://YOUR_IP:8000`

---

**Good luck! Happy chatting with Chiku!** 🚀
