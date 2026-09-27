@echo off
title 3 - Code Doctor Frontend
cd /d %~dp0..\frontend
echo Starting frontend on http://localhost:5173 (keep this window open)...
npm run dev
