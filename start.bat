@echo off
REM ============================================
REM  AI Personal Cloud Drive - Quick Start
REM ============================================
REM  Starts backend + Cloudflare Tunnel + frontend dev server.
REM  For production auto-start, see autostart.bat + Task Scheduler.
REM ============================================

setlocal enabledelayedexpansion

set PROJECT_DIR=%~dp0
set BACKEND_DIR=%PROJECT_DIR%backend
set FRONTEND_DIR=%PROJECT_DIR%frontend

echo.
echo ============================================
echo   AI Personal Cloud Drive
echo ============================================
echo.

REM --- Firewall: Ensure Python is allowed ---
echo [*] Checking Windows Firewall...
netsh advfirewall firewall add rule name="CloudDrive-Python" dir=in action=allow program="%LOCALAPPDATA%\Programs\Python\Python311\python.exe" enable=yes 2>nul
netsh advfirewall firewall add rule name="CloudDrive-Port-8000" dir=in action=allow protocol=TCP localport=8000 enable=yes 2>nul
echo     Firewall rules added (port 8000 TCP).

REM --- Check if frontend is built ---
if not exist "%FRONTEND_DIR%\dist\index.html" (
    echo.
    echo [!] Frontend not built. Building now...
    cd /d "%FRONTEND_DIR%"
    call npm run build
    cd /d "%PROJECT_DIR%"
    echo     Build complete.
)

REM --- Start Backend ---
echo.
echo [1/2] Starting backend (FastAPI)...
echo       Binding to all IPv4 interfaces
echo       Port: 8000 (HTTP)

start "CloudDrive-API" cmd /c "cd /d "%BACKEND_DIR%" && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
echo       Backend started.

REM --- Start Cloudflare Tunnel ---
echo.
echo [2/3] Starting Cloudflare Tunnel...
echo       Domain: files.balabalashowtime.icu
start "CloudDrive-Tunnel" cmd /c "d:\A_VSCode_Projects\AIPersonalCloudDrive\tools\cloudflared.exe tunnel run clouddrive"
echo       Tunnel started.

REM --- Wait for services ---
echo       Waiting for services to be ready...
timeout /t 3 /nobreak >nul

REM --- Start Frontend Dev Server (optional, for hot-reload development) ---
echo [3/3] Starting frontend dev server (Vite)...
start "CloudDrive-Frontend" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev"
echo       Frontend dev server starting on http://127.0.0.1:5173

echo.
echo ============================================
echo   Service URLs:
echo.
echo   Local PC:
echo     http://127.0.0.1:8000
echo.
echo   Phone (same hotspot, fast):
echo     http://<lan-ip>:8000  ^(scan QR code on page^)
echo.
echo   Phone (anywhere):
echo     https://files.balabalashowtime.icu
echo.
echo   Default login: admin / admin123
echo ============================================
echo.
echo Press any key in this window to stop all services.
pause >nul

REM --- Cleanup on exit ---
echo Stopping services...
taskkill /FI "WINDOWTITLE eq CloudDrive-API*" /T 2>nul
taskkill /FI "WINDOWTITLE eq CloudDrive-Tunnel*" /T 2>nul
taskkill /FI "WINDOWTITLE eq CloudDrive-Frontend*" /T 2>nul
echo Done.
