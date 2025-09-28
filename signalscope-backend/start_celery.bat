@echo off
echo Starting Celery Worker and Beat...
echo.
echo This will open 2 new windows:
echo   1. Celery Worker - Processes tasks
echo   2. Celery Beat - Schedules tasks
echo.
pause

cd /d "%~dp0"

REM Start Celery Worker in new window
start "Celery Worker" cmd /k "celery -A app.celery_app worker --loglevel=info --pool=solo"

REM Wait a moment
timeout /t 3 /nobreak >nul

REM Start Celery Beat in new window
start "Celery Beat" cmd /k "celery -A app.celery_app beat --loglevel=info"

echo.
echo Celery services started in separate windows!
echo Close those windows to stop processing.
pause