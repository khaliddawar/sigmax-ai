@echo off
echo Starting Celery Worker for SignalScope...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Start Celery worker
echo Starting Celery worker with all queues...
celery -A app.celery_app worker --loglevel=info --queues=realtime,standard,archive,reports,maintenance --pool=solo

pause