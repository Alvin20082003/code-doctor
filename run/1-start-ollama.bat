@echo off
title 1 - IBM Granite (Ollama)
echo Stopping any old Ollama...
taskkill /F /IM "ollama app.exe" >nul 2>&1
taskkill /F /IM ollama.exe >nul 2>&1
timeout /t 2 /nobreak >nul
set CUDA_VISIBLE_DEVICES=-1
echo Starting IBM Granite server (keep this window open)...
ollama serve
