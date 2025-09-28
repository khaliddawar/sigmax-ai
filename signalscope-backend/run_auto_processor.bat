@echo off
echo ============================================================
echo SignalScope Auto-Processor
echo ============================================================
echo This will automatically process messages every 30 seconds
echo and send reports to your Telegram
echo.
echo Press Ctrl+C to stop
echo ============================================================

cd /d "%~dp0"

:loop
echo.
echo [%TIME%] Checking queues...

python -c "import redis; r = redis.Redis(decode_responses=True); print(f'  Realtime: {r.xlen(\"signalscope:messages:realtime\")} | Standard: {r.xlen(\"signalscope:messages:standard\")} | Archive: {r.xlen(\"signalscope:messages:archive\")}')"

echo   Processing messages if any...
python process_batch.py 2>nul | findstr /v "^$" | findstr /v "="

timeout /t 30 /nobreak >nul
goto loop