
# Chiku: Personal Voice Assistant

## Project Overview
A real-time, dynamic AI voice assistant inspired by Agentic AI companions in this current world and makes the users choices and day better.


## Prerequisites & Constraints
- **Models**: Open-source and free alternatives only
- **Backend**: Research-backed stack with adaptive support for voice, speech, and multimodal models
- **Architecture**: Extensible for future model integrations

## Revised Tech Stack (Open-Source)
- **ASR**: OpenAI Whisper or Coqui STT
- **LLM**: Llama 2, Mistral, or Falcon (via Ollama/Hugging Face)
- **TTS**: Coqui TTS, Bark, or XTTS-v2
- **Runtime**: Python with FastAPI or Node.js
- **Voice Pipeline**: PyAudio + Sounddevice for I/O
- **Orchestration**: Apache Airflow or custom async event dispatcher
- **Model Hub**: Hugging Face Transformers as central registry


## Core Components Needed

### 1. **Speech Recognition**
    - Real-time audio input processing
    - Natural language understanding
    - Noise filtering

### 2. **Language Model/AI Engine**
    - LLM integration (GPT, Claude, or similar)
    - Context awareness and memory
    - Dynamic response generation

### 3. **Text-to-Speech (TTS)**
    - Natural voice synthesis
    - Customizable voice personality
    - Low latency audio output

### 4. **System Integration**
    - Device control capabilities
    - Calendar/reminder access
    - Web search integration
    - Application launching

### 5. **Backend Architecture**
    - WebSocket for real-time communication
    - Session management
    - Response caching

### 6. **Frontend/Interface**
    - Voice activation trigger
    - Visual feedback indicators
    - Conversation history display

## Tech Stack Suggestions
- **ASR**: Whisper (OpenAI) or Google Speech-to-Text
- **LLM**: OpenAI GPT-4, Claude, or local LLaMA
- **TTS**: ElevenLabs, Google Cloud TTS, or Bark
- **Runtime**: Python, Node.js, or Electron
- **Orchestration**: Custom event dispatcher

## Next Steps
1. Select LLM provider
2. Choose speech I/O libraries
3. Design system prompts for Chiku's personality
4. Build real-time streaming pipeline
