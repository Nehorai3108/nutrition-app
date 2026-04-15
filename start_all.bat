@echo off
REM Nutrition App - Dual Environment Startup
REM User App: http://localhost:8501
REM Admin App: http://localhost:8502

echo.
echo ========================================
echo Nutrition App - Separate Environments
echo ========================================
echo.

echo Starting User App on port 8501...
start "User App" cmd /k "cd /d "%~dp0" && streamlit run app_user.py --server.port 8501"

timeout /t 2

echo Starting Admin App on port 8502...
start "Admin App" cmd /k "cd /d "%~dp0" && streamlit run app_admin.py --server.port 8502"

echo.
echo ========================================
echo Environments Started
echo ========================================
echo User App (Nutrition):    http://localhost:8501
echo Admin App (Management):  http://localhost:8502
echo.
echo Close the terminal windows when done.
echo ========================================
echo.

pause
