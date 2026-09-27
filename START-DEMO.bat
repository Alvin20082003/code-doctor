@echo off
title Code Doctor - Launcher
echo ============================================
echo   CODE DOCTOR - starting everything
echo ============================================
echo [1/3] Starting IBM Granite (Ollama)...
start "1 - Ollama" cmd /k "%~dp0run\1-start-ollama.bat"
timeout /t 6 /nobreak >nul
echo [2/3] Starting backend...
start "2 - Backend" cmd /k "%~dp0run\2-start-backend.bat"
timeout /t 6 /nobreak >nul
echo [3/3] Starting frontend...
start "3 - Frontend" cmd /k "%~dp0run\3-start-frontend.bat"
timeout /t 8 /nobreak >nul
echo Opening browser...
start http://localhost:5173
echo.
echo All started. Keep the 3 windows open.
echo Optional: double-click run\4-warmup-granite.bat before a live demo.
pause
