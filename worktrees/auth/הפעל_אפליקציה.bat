@echo off
cd /d "C:\Users\User\Documents\nutrition-app"
start pythonw -m streamlit run app_user.py --server.address 0.0.0.0 --server.port 8501
timeout /t 4 /nobreak > nul
start http://localhost:8501
