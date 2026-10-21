#!/usr/bin/env bash
# One-time setup on macOS or Linux. In Terminal, from this folder:   bash setup.sh
#   1. finds Python 3.12 or newer (offers to get one if this computer has none)
#   2. creates the project's own Python environment (.venv) and installs the packages
#   3. creates .env from .env.example
#   4. runs the automated tests (no AI needed, about 2 minutes)
#   5. gets the local AI model ready (Ollama), or offers to run without AI for now
# Running it again is safe: it keeps what is already done.
set -u
cd "$(dirname "$0")" || exit 1
step() { printf "\n== %s\n" "$1"; }
ask() { local a; read -r -p "$1 [y/N] " a < /dev/tty || a=""; [[ "$a" =~ ^[Yy] ]]; }
fail() { printf "\nSetup stopped: %s\n" "$1"; exit 1; }
ok_version='import sys; sys.exit(0 if (3, 12) <= sys.version_info[:2] < (3, 15) else 1)'

find_python() {
  local c p
  for c in python3.13 python3.12 python3.14 python3 \
           /opt/homebrew/bin/python3 /usr/local/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/3.12/bin/python3; do
    p=$(command -v "$c" 2> /dev/null) || continue
    # On a Mac without the developer tools, /usr/bin/python3 only opens an installer window: skip it
    if [ "$(uname)" = "Darwin" ] && [ "$p" = "/usr/bin/python3" ] && ! xcode-select -p > /dev/null 2>&1; then continue; fi
    "$p" -c "$ok_version" 2> /dev/null && "$p" -c 'import venv, ensurepip' 2> /dev/null && { echo "$p"; return 0; }
  done
  return 1
}

step "1/5 Python"
if [ -x .venv/bin/python ] && .venv/bin/python -c "$ok_version" 2> /dev/null && .venv/bin/python -m pip --version > /dev/null 2>&1; then
  echo "The project environment (.venv) already exists: $(.venv/bin/python --version)"
else
  rm -rf .venv
  PY=$(find_python)
  if [ -n "$PY" ]; then
    echo "Using $PY ($("$PY" --version))"
    "$PY" -m venv .venv || fail "could not create .venv"
  else
    echo "Python 3.12 or newer was not found on this computer."
    UV=$(command -v uv 2> /dev/null || true)
    [ -z "$UV" ] && [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"
    if [ -z "$UV" ]; then
      echo "Setup can get Python for this project only, with the small tool 'uv' (no admin rights needed)."
      echo "Or install Python 3.13 yourself from https://www.python.org/downloads/ and run setup again."
      ask "Download uv and Python 3.13 now?" || fail "no Python 3.12 or newer."
      tmp=$(mktemp)
      curl -LsSf -o "$tmp" https://astral.sh/uv/install.sh || fail "could not download uv (check the internet connection)"
      env UV_NO_MODIFY_PATH=1 sh "$tmp" || fail "could not install uv"
      rm -f "$tmp"
      UV="$HOME/.local/bin/uv"
    fi
    "$UV" venv --seed --python 3.13 .venv || fail "could not create .venv with uv"
  fi
fi

step "2/5 Packages (a few minutes the first time)"
.venv/bin/python -m pip install --disable-pip-version-check -q --upgrade pip
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt \
  || fail "package install failed (check the internet connection and run setup again)"

step "3/5 Settings"
if [ -f .env ]; then echo ".env already exists (kept as it is)"; else cp .env.example .env && echo "Created .env from .env.example"; fi
mkdir -p logs runtime

step "4/5 Automated tests (no AI needed, about 2 minutes)"
if .venv/bin/python -m pytest -q -p no:cacheprovider; then TESTS="all passed"; else TESTS="SOME FAILED (see above)"; fi

step "5/5 AI model"
.venv/bin/python scripts/start_ai.py --setup || true

printf "\n== Setup finished. Tests: %s\n" "$TESTS"
echo "Start the portal with:   bash run_app.sh"
echo "It opens in your browser at http://localhost:8501"
