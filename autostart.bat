@echo off
REM Auto-start script for Task Scheduler (runs at user login)
cd /d "%~dp0"

REM Start backend (hidden window, HTTP)
start "" /MIN cmd /c "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

REM Start Cloudflare Tunnel (hidden window)
if exist "tools\cloudflared.exe" (
    start "" /MIN cmd /c "tools\cloudflared.exe tunnel run clouddrive"
)
