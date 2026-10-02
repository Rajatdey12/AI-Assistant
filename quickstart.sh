#!/bin/bash
# Chiku Quick Start Script - Use this to run Chiku locally
# Works on macOS and Linux. Windows users see instructions below.

echo "╔════════════════════════════════════════════════╗"
echo "║    🎤 CHIKU - Voice Assistant Quick Start 🎤   ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check Python
echo "✓ Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "  Found: $PYTHON_VERSION"
echo ""

# Create venv
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "✓ Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "✓ Installing dependencies (this takes 15-20 minutes on first run)..."
echo "  - Downloading AI models (~7GB total)"
echo "  - Please wait..."
echo ""
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo "✅ Dependencies installed!"
echo ""

# Check Ollama
echo "✓ Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama not installed in PATH"
    echo "   Download from: https://ollama.ai"
    echo ""
fi

# Verify models
echo "✓ Verifying model availability..."
python3 client.py --test-models
echo ""

echo "╔════════════════════════════════════════════════╗"
echo "║ ✅ Setup Complete! Ready to run Chiku         ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "📋 Next Steps (Run these in separate terminals):"
echo ""
echo "1️⃣  Terminal 1 - Start Ollama (if not already running):"
echo "    ollama serve"
echo ""
echo "2️⃣  Terminal 2 - Start Chiku Server:"
echo "    source venv/bin/activate"
echo "    python server.py"
echo ""
echo "3️⃣  Terminal 3 - Run Chiku Voice Client:"
echo "    source venv/bin/activate"
echo "    python client.py --voice"
echo ""
echo "💡 Pro Tips:"
echo "   • Use text mode if voice isn't working: client.py --text"
echo "   • Test audio: client.py --test-audio"
echo "   • See previous chats: client.py --list-sessions"
echo ""
echo "📖 Full docs: Read README.md or SETUP.md"
echo ""
echo "Enjoy! 🎤🤖"
