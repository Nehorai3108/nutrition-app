@echo off
REM ── BiteFit API server ──────────────────────────────────────────
REM הפעל את הקובץ הזה בדאבל-קליק. השאר את החלון פתוח כל עוד אתה עובד.
REM משתמש ב-python הנכון (pythoncore) שמורשה ב-Firewall כדי שהטלפון יגיע.

cd /d "%~dp0"

set PY="C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe"

echo ================================================
echo   BiteFit API  -  http://0.0.0.0:8000
echo   Tailscale:    http://100.65.59.37:8000
echo   להשאיר את החלון פתוח! לעצירה: Ctrl+C
echo ================================================
echo.

%PY% -m uvicorn api.main:app --host 0.0.0.0 --port 8000

echo.
echo *** השרת נעצר. לחץ מקש כלשהו לסגירה. ***
pause >nul
