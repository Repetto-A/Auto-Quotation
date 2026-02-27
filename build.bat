@echo off
setlocal

echo Preparando entorno de desarrollo...
echo.

echo [1/2] Backend en ventana separada...
start "Backend - build" cmd /k "cd /d d:\Usuario\Desktop\cotibot2.0-dev\backend && python -m venv venv && call .\venv\Scripts\activate && pip install -r requirements.txt"

echo [2/2] Frontend en ventana separada...
start "Frontend - build" cmd /k "cd /d d:\Usuario\Desktop\cotibot2.0-dev\frontend && pnpm install"

echo.
echo Instalaciones lanzadas en paralelo.
echo Revisa ambas ventanas para confirmar que terminaron sin errores.
endlocal
