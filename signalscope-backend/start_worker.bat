@echo off
title SignalScope Worker
echo ============================================================
echo           SIGNALSCOPE AUTOMATIC WORKER
echo ============================================================
echo.
echo This worker will automatically:
echo   - Check for new trading messages every 30 seconds
echo   - Process high-priority messages every 5 minutes
echo   - Generate hourly reports every 15 minutes
echo   - Send all reports to your Telegram
echo.
echo Keep this window open for continuous processing!
echo Press Ctrl+C to stop
echo ============================================================
echo.

cd /d "%~dp0"
python worker.py

pause