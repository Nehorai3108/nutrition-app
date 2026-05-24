@echo off
cd /d "%~dp0"
start pythonw -m streamlit run app_user.py --server.address 0.0.0.0 --server.port 8510
timeout /t 4 /nobreak > nul
start http://localhost:8510
