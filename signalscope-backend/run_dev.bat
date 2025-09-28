@echo off
echo Starting SignalScope Backend...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the FastAPI application
echo Starting FastAPI server on http://localhost:8000
echo Press Ctrl+C to stop
echo.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000