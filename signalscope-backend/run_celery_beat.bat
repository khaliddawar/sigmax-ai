@echo off
echo Starting Celery Beat Scheduler for SignalScope...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Start Celery beat (scheduler)
echo Starting Celery beat scheduler for periodic tasks...
celery -A app.celery_app beat --loglevel=info

pause