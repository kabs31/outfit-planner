@echo off
echo Starting AI Outfit App...
echo.
echo Starting Ollama...
start "Ollama" cmd /k ollama serve
timeout /t 3 /nobreak > nul

echo Starting Backend...
start "Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload"
timeout /t 5 /nobreak > nul

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================================
echo All services started!
echo ============================================================
echo.
echo Open http://localhost:5173 in your browser
echo.
echo To stop: Close all terminal windows
echo ============================================================
pause
