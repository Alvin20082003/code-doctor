@echo off
title 4 - Warm up Granite
cd /d %~dp0..\backend
echo Warming up IBM Granite with the demo code (takes 1-2 min the first time)...
venv\Scripts\python.exe scripts\smoke_test.py hero_endpoint
echo.
echo Done. If you see "verified" above, you are ready to demo.
pause
