@echo off
REM Chiku Quick Start Script - Windows Batch Version
REM Run this file to set up and prepare Chiku

setlocal enabledelayedexpansion

cls
echo.
echo ╔════════════════════════════════════════════════╗
echo ║    🎤 CHIKU - Voice Assistant Quick Start 🎤   ║
echo ╚════════════════════════════════════════════════╝
echo.

REM Check Python
echo ✓ Checking Python version...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.9+ from python.org
    pause
    exit /b 1
)
python --version
echo.

REM Create venv
if not exist "venv" (
    echo ✓ Creating virtual environment...
    python -m venv venv
)

REM Activate venv
echo ✓ Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo ✓ Installing dependencies (this takes 15-20 minutes on first run)...
echo   - Downloading AI models (~7GB total^)
echo   - Please wait...
echo.
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed!
echo.

REM Verify models
echo ✓ Verifying model availability...
python client.py --test-models
echo.

cls
echo.
echo ╔════════════════════════════════════════════════╗
echo ║ ✅ Setup Complete! Ready to run Chiku         ║
echo ╚════════════════════════════════════════════════╝
echo.
echo 📋 Next Steps (Run these in separate PowerShell windows^):
echo.
echo 1️⃣  Window 1 - Start Ollama:
echo     ollama serve
echo.
echo 2️⃣  Window 2 - Activate venv and start server:
echo     cd chiku-assistant
echo     .\venv\Scripts\Activate.ps1
echo     python server.py
echo.
echo 3️⃣  Window 3 - Activate venv and run client:
echo     cd chiku-assistant
echo     .\venv\Scripts\Activate.ps1
echo     python client.py --voice
echo.
echo 💡 Pro Tips:
echo    • Use text mode: python client.py --text
echo    • Test audio: python client.py --test-audio
echo    • List conversations: python client.py --list-sessions
echo.
echo 📖 Full docs: Read README.md or SETUP.md
echo.
echo Enjoy! 🎤🤖
echo.
pause
