@echo off
REM ============================================
REM  AI Personal Cloud Drive - Quick Start
REM ============================================
REM  Starts both backend and frontend dev server.
REM  For production deployment, see install-service.bat
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
echo       Binding to all interfaces (IPv6 + IPv4)
echo       Port: 8000
start "CloudDrive-API" cmd /c "cd /d "%BACKEND_DIR%" && python -m uvicorn main:app --host :: --port 8000"
echo       Backend started.

REM --- Wait for backend ---
echo       Waiting for backend to be ready...
timeout /t 3 /nobreak >nul

REM --- Start Frontend Dev Server (optional, for hot-reload development) ---
echo [2/2] Starting frontend dev server (Vite)...
start "CloudDrive-Frontend" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev"
echo       Frontend dev server starting on http://127.0.0.1:5173

echo.
echo ============================================
echo   Service URLs:
echo.
echo   Local access:
echo     http://127.0.0.1:8000
echo     http://[::1]:8000
echo.
echo   API Docs:
echo     http://127.0.0.1:8000/docs
echo.
echo   Public Status:
echo     http://127.0.0.1:8000/api/public-status
echo.
echo   Dev Frontend (hot reload):
echo     http://127.0.0.1:5173
echo.
echo   Default login: admin / admin123
echo ============================================
echo.
echo Check public accessibility:
echo   1. Ensure phone hotspot is connected
echo   2. Check http://127.0.0.1:8000/api/public-status
echo   3. Wait for DDNS to update (3 min)
echo   4. Access: http://files.balabalashowtime.icu:8000
echo.
echo Press any key in this window to stop all services.
pause >nul

REM --- Cleanup on exit ---
echo Stopping services...
taskkill /FI "WINDOWTITLE eq CloudDrive-API*" /T 2>nul
taskkill /FI "WINDOWTITLE eq CloudDrive-Frontend*" /T 2>nul
echo Done.
