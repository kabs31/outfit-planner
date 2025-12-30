@echo off
cd /d "C:\Users\Kabilan D\OneDrive\Desktop\outfit-planner\backend"
call venv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 8001
pause
