@echo off
REM ============================================================
REM  BiteFit - start both servers for the mobile app
REM    1) FastAPI backend  (data)  -> port 8000
REM    2) Expo / Metro     (app)   -> port 8081
REM  Each opens in its own window so you can read the logs.
REM ============================================================

set BACKEND_DIR=C:\Users\User\Documents\nutrition-app
set MOBILE_DIR=C:\Users\User\Documents\bitefit-mobile
set TAILSCALE_IP=100.65.59.37

echo.
echo ============================================================
echo   BiteFit - starting backend + app
echo ============================================================
echo.

echo Starting FastAPI backend on port 8000 (no --reload)...
start "BiteFit API (8000)" cmd /k "cd /d "%BACKEND_DIR%" && set PUBLIC_BASE_URL=http://%TAILSCALE_IP%:8000 && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 >nul

echo Starting Expo / Metro bundler on port 8081...
start "BiteFit App (Expo)" cmd /k "cd /d "%MOBILE_DIR%" && npx expo start --port 8081"

echo.
echo ============================================================
echo   Both servers launching in separate windows.
echo.
echo   On the phone (same Tailscale network) open:
echo     exp://%TAILSCALE_IP%:8081      (Expo Go)
echo   Backend health check (in browser):
echo     http://localhost:8000/docs
echo.
echo   Close those two windows to stop the servers.
echo ============================================================
echo.
pause
