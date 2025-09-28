@echo off
echo.
echo ===============================================
echo SignalScope Backend Setup for Windows
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from python.org
    pause
    exit /b 1
)

echo [1/5] Creating Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/5] Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [4/5] Creating .env file from template...
if not exist ".env" (
    copy .env.example .env
    echo .env file created. Please edit it with your API keys.
) else (
    echo .env file already exists.
)

echo.
echo ===============================================
echo Setup Complete!
echo ===============================================
echo.
echo Next steps:
echo 1. Download Redis for Windows from:
echo    https://github.com/microsoftarchive/redis/releases
echo    OR use Memurai (Redis for Windows): https://www.memurai.com/
echo.
echo 2. Edit the .env file with your API keys:
echo    - OPENAI_API_KEY
echo    - SUPABASE_URL and SUPABASE_KEY
echo.
echo 3. Start Redis (if using Redis for Windows):
echo    redis-server.exe
echo.
echo 4. In a new terminal, run the backend:
echo    venv\Scripts\activate
echo    python -m uvicorn app.main:app --reload
echo.
echo The API will be available at: http://localhost:8000
echo API documentation at: http://localhost:8000/docs
echo.
pause