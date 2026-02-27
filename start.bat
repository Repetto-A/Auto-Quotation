@echo off

echo Iniciando servidor de desarrollo...
echo.

echo [1/2] Ejecutando npm run dev (Frontend)...
start "Frontend - npm dev" cmd /k "cd frontend && call npm run dev"

echo [2/2] Ejecutando backend (Uvicorn)...
cmd /k "cd backend && call .\venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0"

echo.
echo Presiona cualquier tecla para salir...
pause >nul