@echo off
REM Starts the portal (Windows). Double-click this file.
REM Gets the AI model ready first, then opens http://localhost:8501 in your browser.
REM Keep this window open while you use the portal; close it to stop the portal.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Run setup.bat first. & pause & exit /b 1)
.venv\Scripts\python scripts\start_ai.py
if errorlevel 1 echo [AI] The AI is not ready. The portal still opens; Demo controls shows the AI status and can switch to scripted (no AI).
.venv\Scripts\python -m streamlit run app.py --server.address localhost
pause
