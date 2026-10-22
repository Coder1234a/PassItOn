@echo off
REM One-click setup and start for PassItOn on Windows.
cd /d "%~dp0"
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv || (echo Python not found. Install Python 3.11+ and tick "Add Python to PATH". & pause & exit /b 1)
)
call venv\Scripts\activate
echo Installing requirements (first run takes a few minutes)...
pip install -q -r requirements.txt || (echo pip install failed - check your internet. & pause & exit /b 1)
REM Opens the two-phone demo page once the server is up.
start "" cmd /c "timeout /t 4 >nul & start http://localhost:5000/demo"
python server.py
pause
