"""Gets the AI model ready before the portal starts. Works on macOS, Windows and Linux.

Run by setup (setup.sh / setup.bat) and by the start scripts (run_app.sh / run_app.bat); safe to run any time:

    python scripts/start_ai.py            start the local AI server if needed, then load the model
    python scripts/start_ai.py --setup    the same, and also offers to download the model or install Ollama

What it does depends on LLM_PROVIDER in .env:
  ollama     finds Ollama, starts its server if it is not running, downloads the model if it is missing
             (asks first: about 5 GB), then loads it into memory so the first reply is not slow
  hosted     checks that HOSTED_API_KEY is set (a hosted model such as Groq or Gemini, used by the online copy)
  anthropic  checks that ANTHROPIC_API_KEY is set
  scripted   nothing to do (no AI model; a fixed rule-following planner)

Exit code 0 means the AI is ready. Otherwise the portal still opens, and the AI status shows in Demo controls,
where the model can also be switched to "scripted" (no AI).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
SYSTEM = platform.system()            # "Darwin" (macOS), "Windows" or "Linux"

try:
    import requests
    from dotenv import dotenv_values
except ImportError:                    # run with the project's Python (.venv), which setup creates
    print("[AI] Run setup first (setup.sh on macOS/Linux, setup.bat on Windows).")
    sys.exit(1)


def say(msg: str) -> None:
    print(f"[AI] {msg}", flush=True)


def env() -> dict:
    return {k: (v or "").strip() for k, v in dotenv_values(ENV).items()} if ENV.exists() else {}


def set_env(key: str, value: str) -> None:
    """Change one setting in .env, keeping every other line as it is."""
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ask(question: str, default: bool = False) -> bool:
    """Yes or no question. With no keyboard (for example when run by another program) the default is used."""
    if not sys.stdin or not sys.stdin.isatty():
        return default
    hint = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"[AI] {question} {hint} ").strip().lower()
    except EOFError:
        return default
    return default if not answer else answer.startswith("y")


# ------------------------------------------------------------------ finding and starting Ollama
def find_ollama(cfg: dict) -> str | None:
    places = []
    if cfg.get("OLLAMA_DIR"):
        places.append(Path(cfg["OLLAMA_DIR"]) / ("ollama.exe" if SYSTEM == "Windows" else "ollama"))
    found = shutil.which("ollama")
    if found:
        places.append(Path(found).resolve())          # on macOS this is a link into Ollama.app
    if SYSTEM == "Darwin":
        places += [Path("/Applications/Ollama.app/Contents/Resources/ollama"),
                   Path.home() / "Applications/Ollama.app/Contents/Resources/ollama",
                   Path("/opt/homebrew/bin/ollama"), Path("/usr/local/bin/ollama")]
    elif SYSTEM == "Windows":
        places.append(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe")
    else:
        places += [Path("/usr/local/bin/ollama"), Path("/usr/bin/ollama")]
    for p in places:
        if p.is_file():
            return str(p)
    return None


def server_up(url: str) -> bool:
    try:
        return requests.get(f"{url}/api/version", timeout=2).ok
    except requests.exceptions.RequestException:
        return False


def start_server(exe: str, cfg: dict) -> None:
    child_env = dict(os.environ)
    if cfg.get("OLLAMA_MODELS") and Path(cfg["OLLAMA_MODELS"]).is_dir():   # optional: models on another drive
        child_env["OLLAMA_MODELS"] = cfg["OLLAMA_MODELS"]
    app_mac = Path(exe).parents[2] if SYSTEM == "Darwin" and ".app/" in exe else None
    app_win = Path(exe).with_name("ollama app.exe") if SYSTEM == "Windows" else None
    if app_mac and app_mac.suffix == ".app":
        subprocess.run(["open", "-g", "-a", str(app_mac)], check=False)   # menu bar app; runs in the background
        return
    if app_win and app_win.is_file():
        subprocess.Popen([str(app_win)], env=child_env, close_fds=True,  # tray app (icon near the clock)
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        return
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log = open(log_dir / "ollama_server.log", "ab")    # noqa: SIM115  (kept open by the server process)
    kw = {"creationflags": getattr(subprocess, "DETACHED_PROCESS", 0)} if SYSTEM == "Windows" else \
        {"start_new_session": True}
    subprocess.Popen([exe, "serve"], stdout=log, stderr=log, stdin=subprocess.DEVNULL, env=child_env, **kw)


def installed_models(url: str) -> list[str]:
    try:
        return [m.get("name", "") for m in requests.get(f"{url}/api/tags", timeout=5).json().get("models", [])]
    except (requests.exceptions.RequestException, ValueError):
        return []


def has_model(url: str, model: str) -> bool:
    names = installed_models(url)
    return model in names or (":" not in model and f"{model}:latest" in names)


def pull(url: str, model: str) -> bool:
    say(f"Downloading {model}. This happens once and can take a while on a slow connection...")
    last = -5
    try:
        with requests.post(f"{url}/api/pull", json={"model": model, "stream": True}, stream=True, timeout=60) as r:
            for line in r.iter_lines():
                if not line:
                    continue
                msg = json.loads(line)
                if msg.get("error"):
                    say(f"Download failed: {msg['error']}")
                    return False
                if msg.get("total") and msg.get("completed") is not None:
                    pct = int(100 * msg["completed"] / msg["total"])
                    if pct >= last + 5:
                        last = pct
                        say(f"  {pct}%  ({msg['total'] / 1e9:.1f} GB part)")
                elif msg.get("status"):
                    say(f"  {msg['status']}")
    except requests.exceptions.RequestException as e:
        say(f"Download stopped ({e.__class__.__name__}). Run this again to continue where it stopped.")
        return False
    return has_model(url, model)


def warm(url: str, model: str) -> bool:
    say(f"Loading {model} into memory (up to a minute or two the first time)...")
    try:
        requests.post(f"{url}/api/generate", json={"model": model, "keep_alive": "30m"}, timeout=300).raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        say(f"Could not load the model ({e.__class__.__name__}).")
        return False


def explain_install(setup: bool) -> None:
    say("Ollama (the free program that runs the AI model on this computer) is not installed.")
    if SYSTEM == "Darwin":
        say("Install it from https://ollama.com/download (drag Ollama to Applications and open it once).")
    elif SYSTEM == "Windows":
        say("Install it from https://ollama.com/download, or in a terminal:  winget install -e --id Ollama.Ollama")
    else:
        say("Install it with:  curl -fsSL https://ollama.com/install.sh | sh")
    if setup and sys.stdin.isatty() and SYSTEM in ("Darwin", "Windows") and ask("Open the Ollama download page now?", default=True):
        webbrowser.open("https://ollama.com/download")


def no_ai_fallback(setup: bool) -> None:
    if setup and ask("Use the portal without an AI model for now (LLM_PROVIDER=scripted)? "
                     "You can switch later in .env or in Demo controls.", default=True):
        set_env("LLM_PROVIDER", "scripted")
        say("Saved LLM_PROVIDER=scripted in .env. After installing Ollama, set it back to ollama and run setup again.")


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--setup", action="store_true", help="also offer to install Ollama and download the model")
    args = ap.parse_args()
    cfg = env()
    provider = cfg.get("LLM_PROVIDER", "ollama").lower() or "ollama"

    if provider == "scripted":
        say("LLM_PROVIDER=scripted: no AI model is used (fixed rule-following planner). Nothing to start.")
        return 0
    if provider == "anthropic":
        if cfg.get("ANTHROPIC_API_KEY"):
            say("LLM_PROVIDER=anthropic: the Claude API key is set.")
            return 0
        say("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty in .env. Add the key, or use ollama or scripted.")
        return 1
    if provider == "hosted":
        if cfg.get("HOSTED_API_KEY") or cfg.get("GROQ_API_KEY"):
            say(f"LLM_PROVIDER=hosted: the API key is set (model {cfg.get('HOSTED_MODEL') or 'openai/gpt-oss-120b'}).")
            return 0
        say("LLM_PROVIDER=hosted but HOSTED_API_KEY is empty in .env. Add the key, or use ollama or scripted.")
        return 1
    if provider != "ollama":
        say(f"Unknown LLM_PROVIDER '{provider}' in .env (use ollama, hosted, anthropic or scripted).")
        return 1

    url = (cfg.get("OLLAMA_URL") or "http://localhost:11434").rstrip("/")
    model = cfg.get("OLLAMA_MODEL") or "qwen3:8b"

    if not server_up(url):
        exe = find_ollama(cfg)
        if not exe:
            explain_install(args.setup)
            no_ai_fallback(args.setup)
            return 1
        say("Starting the local AI server (Ollama)...")
        start_server(exe, cfg)
        for _ in range(60):
            time.sleep(1)
            if server_up(url):
                break
        else:
            say("The local AI server did not start within 60 seconds. Open the Ollama app, then try again.")
            return 1
    say("Local AI server is running.")

    if not has_model(url, model):
        say(f"The model {model} is not downloaded yet (about 5 GB on disk; it needs about 8 GB of memory).")
        if not ask(f"Download {model} now?", default=args.setup):
            say(f"Skipped. Download it later with:  ollama pull {model}")
            no_ai_fallback(args.setup)
            return 1
        if not pull(url, model):
            return 1
    if not warm(url, model):
        return 1
    say(f"Ready: {model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
