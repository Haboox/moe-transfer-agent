@echo off
REM One-time setup on Windows. Double-click this file, or run it from a terminal in this folder.
REM   1. finds Python 3.12 or newer (offers to get one if this computer has none)
REM   2. creates the project's own Python environment (.venv) and installs the packages
REM   3. creates .env from .env.example
REM   4. runs the automated tests (no AI needed, about 2 minutes)
REM   5. gets the local AI model ready (Ollama), or offers to run without AI for now
REM Running it again is safe: it keeps what is already done.
setlocal
cd /d "%~dp0"
set "OKV=import sys; sys.exit(0 if (3, 12) <= sys.version_info[:2] < (3, 15) else 1)"

echo.
echo == 1/5 Python
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python -c "%OKV%" >nul 2>&1 && .venv\Scripts\python -m pip --version >nul 2>&1 && (
    echo The project environment .venv already exists.
    goto packages
  )
  rmdir /s /q .venv
)
set "PY="
for %%v in (3.13 3.12 3.14) do if not defined PY (py -%%v -c "%OKV%" >nul 2>&1 && set "PY=py -%%v")
if not defined PY (python -c "%OKV%" >nul 2>&1 && set "PY=python")
if defined PY (
  echo Using %PY%
  %PY% -m venv .venv || (echo Could not create .venv & goto stop)
  goto packages
)
echo Python 3.12 or newer was not found on this computer.
set "UV="
where uv >nul 2>&1 && set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV (
  echo Setup can get Python for this project only, with the small tool "uv" ^(no admin rights needed^).
  echo Or install Python 3.13 yourself from https://www.python.org/downloads/ and run setup again.
  choice /c YN /n /m "Download uv and Python 3.13 now? [Y/N] "
  if errorlevel 2 goto stop
  powershell -NoProfile -ExecutionPolicy ByPass -Command "$env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex" || (echo Could not download uv & goto stop)
  set "UV=%USERPROFILE%\.local\bin\uv.exe"
)
"%UV%" venv --seed --python 3.13 .venv || (echo Could not create .venv with uv & goto stop)

:packages
echo.
echo == 2/5 Packages (a few minutes the first time)
.venv\Scripts\python -m pip install --disable-pip-version-check -q --upgrade pip
.venv\Scripts\python -m pip install --disable-pip-version-check -r requirements.txt || (echo Package install failed: check the internet connection and run setup again. & goto stop)

echo.
echo == 3/5 Settings
if exist .env (echo .env already exists ^(kept as it is^)) else (copy .env.example .env >nul & echo Created .env from .env.example)
if not exist logs mkdir logs
if not exist runtime mkdir runtime

echo.
echo == 4/5 Automated tests (no AI needed, about 2 minutes)
set "TESTS=all passed"
.venv\Scripts\python -m pytest -q -p no:cacheprovider || set "TESTS=SOME FAILED (see above)"

echo.
echo == 5/5 AI model
.venv\Scripts\python scripts\start_ai.py --setup

echo.
echo == Setup finished. Tests: %TESTS%
echo Start the portal by double-clicking run_app.bat
echo It opens in your browser at http://localhost:8501
pause
exit /b 0

:stop
echo.
echo Setup stopped. Fix the problem above and run setup.bat again.
pause
exit /b 1
