@echo off
title 2 - Code Doctor Backend
cd /d %~dp0..\backend
echo Starting backend on http://localhost:8000 (keep this window open)...
venv\Scripts\python.exe -m uvicorn main:app --reload
