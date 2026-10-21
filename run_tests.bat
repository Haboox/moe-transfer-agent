@echo off
REM Runs all automated tests (no AI model needed, about 2 minutes). Full output saved to logs\test_output.txt
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Run setup.bat first. & pause & exit /b 1)
if not exist logs mkdir logs
.venv\Scripts\python -m pytest -p no:cacheprovider -v > logs\test_output.txt 2>&1
type logs\test_output.txt | findstr /R /C:"passed" /C:"failed" /C:"error"
echo Full output: logs\test_output.txt
pause
