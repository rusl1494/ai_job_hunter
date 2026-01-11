@echo off
cd /d "%~dp0"
echo Starting Job Hunter in Docker...
docker run --rm --shm-size=2g --env-file .env -v "%~dp0jobs.db:/app/jobs.db" job-hunter-final
timeout /t 10