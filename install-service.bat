@echo off
REM ============================================
REM  AI Personal Cloud Drive - Install as Windows Services
REM ============================================
REM  Prerequisites:
REM    - NSSM (nssm.cc) downloaded to tools\nssm.exe
REM    - Run as Administrator
REM
REM  This registers the FastAPI backend as a Windows Service
REM  that auto-starts on boot and auto-restarts on crash.
REM
REM  Nginx is optional for MVP — FastAPI directly serves the
REM  frontend and handles public requests on port 8000.
REM ============================================

setlocal

set PROJECT_DIR=%~dp0
set NSSM=%PROJECT_DIR%tools\nssm.exe
set PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe

if not exist "%NSSM%" (
    echo.
    echo [ERROR] NSSM not found at: %NSSM%
    echo.
    echo Download NSSM from: https://nssm.cc/download
    echo Extract nssm.exe to: %PROJECT_DIR%tools\
    echo.
    pause
    exit /b 1
)

if not exist "%PYTHON%" (
    echo [WARN] Python not found at: %PYTHON%
    echo        Trying system Python...
    set PYTHON=python
)

echo.
echo ============================================
echo   AI Personal Cloud Drive - Service Installer
echo ============================================
echo.
echo   Project: %PROJECT_DIR%
echo   Python:  %PYTHON%
echo   NSSM:    %NSSM%
echo.

REM --- Remove existing service if present ---
"%NSSM%" status CloudDrive-API >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [*] Removing existing CloudDrive-API service...
    "%NSSM%" stop CloudDrive-API 2>nul
    "%NSSM%" remove CloudDrive-API confirm 2>nul
)

REM --- Install FastAPI Service ---
echo [1/2] Installing CloudDrive-API service...
"%NSSM%" install CloudDrive-API "%PYTHON%" "-m uvicorn main:app --host :: --port 8000"
"%NSSM%" set CloudDrive-API AppDirectory "%PROJECT_DIR%backend"
"%NSSM%" set CloudDrive-API DisplayName "AI Cloud Drive - API Service"
"%NSSM%" set CloudDrive-API Description "AI Personal Cloud Drive backend API server"
"%NSSM%" set CloudDrive-API Start SERVICE_AUTO_START
"%NSSM%" set CloudDrive-API AppExit Default Restart
"%NSSM%" set CloudDrive-API AppRestartDelay 10000
echo       CloudDrive-API installed (auto-start + auto-restart).

REM --- Configure Firewall ---
echo [2/2] Configuring Windows Firewall...
netsh advfirewall firewall add rule name="CloudDrive-API-Port-8000" dir=in action=allow protocol=TCP localport=8000 enable=yes 2>nul
echo       Port 8000 opened for inbound TCP traffic.

echo.
echo ============================================
echo   Installation complete!
echo.
echo   Service: CloudDrive-API
echo     Status:  nssm status CloudDrive-API
echo     Start:   nssm start CloudDrive-API
echo     Stop:    nssm stop CloudDrive-API
echo     Remove:  nssm remove CloudDrive-API confirm
echo.
echo   Start the service now?
echo     nssm start CloudDrive-API
echo.
echo   After starting, check:
echo     http://127.0.0.1:8000/api/public-status
echo ============================================
echo.
pause
