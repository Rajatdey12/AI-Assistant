# 🚀 Chiku Voice Assistant - Quick Start Guide

## ✅ Prerequisites (Already Done)
- Python 3.11 installed
- Ollama installed with Mistral-7B model
- Virtual environment created with dependencies
- ASR switched to Google Speech API
- TTS made optional

## 🎯 3-Step Startup Process

### Step 1: Choose your LLM backend
Chiku now supports both local Ollama and remote open-source model adapters.

- **Local Ollama** (default)
  - Use local Ollama for inference with no remote API key required.
  - Ensure `config.py` contains:
    ```python
    LLM = {
        "backend": "ollama",
        "model": "mistral:7b",
        "api_key": "",
        "temperature": 0.7,
        "top_p": 0.9,
        "num_predict": 256,
        "num_ctx": 2048,
    }
    ```
  - You can also override via environment variables if you prefer:
    ```powershell
    $env:LLM_BACKEND = "ollama"
    $env:LLM_MODEL = "mistral:7b"
    ```
  - Start Ollama locally:
    ```powershell
    C:\Users\rajat\AppData\Local\Programs\Ollama\ollama.exe serve
    ```
  - Expected output:
    ```
    2026/04/10 15:30:00 routes.go:1008: INFO server config env="1"
    2026/04/10 15:30:00 routes.go:1015: INFO listening on 127.0.0.1:11434
    ```

- **Remote adapter**
  - If you prefer server-based inference, set `LLM["backend"] = "huggingface"` or `LLM["backend"] = "openai"` in `config.py`, or export `LLM_BACKEND=huggingface`/`LLM_BACKEND=openai`.
  - For Hugging Face, set `LLM["model"]` to the desired open-source model name.
  - For OpenAI/ChatGPT, set `LLM["model"]` to a valid OpenAI chat model like `gpt-4o-mini` or `gpt-4.1-mini`.
  - If the remote provider requires authentication, set `LLM_API_KEY` in your environment or `.env` file.
  - No local Ollama server is needed for remote mode.

  **Example PowerShell commands:**
  ```powershell
  cd C:\Users\rajat\OneDrive\Documents\Projects\AI-Assistant\chiku-assistant
  $env:LLM_BACKEND = "openai"
  $env:LLM_MODEL = "gpt-4o-mini"
  $env:LLM_API_KEY = "sk_your_openai_api_key"
  .\venv\Scripts\python.exe server.py
  ```

  **Or add to `.env`:**
  ```text
  LLM_BACKEND=openai
  LLM_MODEL=gpt-4o-mini
  LLM_API_KEY=sk_your_openai_api_key
  ```

  - Get your OpenAI API key from https://platform.openai.com/account/api-keys.
  - Get your Hugging Face API token from https://huggingface.co/settings/tokens.

### Step 2: Start Chiku Server
**Open new terminal/command prompt:**
```
cd C:\Users\rajat\OneDrive\Documents\Projects\AI-Assistant\chiku-assistant
.\venv\Scripts\python.exe server.py
```
**Expected Output:**
```
✅ Config loaded successfully
🚀 Starting server on 0.0.0.0:8000
🌐 Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Step 3: Start Chiku Client
**Open new terminal/command prompt:**
```
cd C:\Users\rajat\OneDrive\Documents\Projects\AI-Assistant\chiku-assistant
.\venv\Scripts\python.exe client.py --voice
```
**Expected Output:**
```
╔════════════════════════════════════════════════╗
║           🎤 CHIKU - Voice Assistant 🎤       ║
║        Inspired by Real world AI companions.   ║
╚════════════════════════════════════════════════╝

📍 Session: default
🌐 Server: ws://localhost:8000

🎤 Voice Mode
   - Speak clearly
   - Chiku responds with speech (Press Ctrl+C to exit)

🎤 Listening... speak now
```

## 🎤 How to Use

1. **Wait for "🎤 Listening... speak now"**
2. **Speak clearly:** "Hello Chiku, what's the weather?"
3. **System detects silence** (~500ms) and processes
4. **Hear response** (or see text if TTS unavailable)
5. **Continue conversation** - context is maintained

## 🛠️ Troubleshooting

### "Connection refused"
- If using **local Ollama**, ensure Ollama is running in Step 1
- If using **remote backend**, ensure `LLM["backend"]` and `LLM["model"]` are correct in `config.py`
- If using Hugging Face, ensure `LLM_API_KEY` is configured and valid
- Check network connectivity if the remote backend is used

### "Server not responding"
- Verify server started successfully in Step 2
- Check if port 8000 is available

### "Audio device error"
- Check microphone permissions
- Run: `python client.py --test-audio`

### "No speech detected"
- Speak louder/clearer
- Check microphone levels
- Adjust silence detection in `config.py`

## 📁 File Locations
- **Project:** `C:\Users\rajat\OneDrive\Documents\Projects\AI-Assistant\chiku-assistant`
- **Virtual Env:** `chiku-assistant\venv\`
- **Ollama:** `C:\Users\rajat\AppData\Local\Programs\Ollama\`
- **Python:** `C:\Users\rajat\AppData\Local\Programs\Python\Python312\`

## 🔧 Configuration
Edit `config.py` to customize:
- Audio settings (silence detection, sample rate)
- LLM settings (model, temperature)
- TTS settings (voice, language)

## 📝 Notes
- **Internet required** for Google Speech API transcription
- **TTS optional** - responses work as text if TTS fails
- **Sessions saved** in `conversations/` folder
- **Press Ctrl+C** to exit client

---
**Ready to start? Follow Steps 1-3 above!** 🎤🤖