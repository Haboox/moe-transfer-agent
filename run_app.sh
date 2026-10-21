#!/usr/bin/env bash
# Starts the portal (macOS or Linux). In Terminal, from this folder:   bash run_app.sh
# Gets the AI model ready first, then opens http://localhost:8501 in your browser.
# Keep the Terminal window open while you use the portal; press Ctrl+C there to stop it.
cd "$(dirname "$0")" || exit 1
[ -x .venv/bin/python ] || { echo "Run the setup first:   bash setup.sh"; exit 1; }
.venv/bin/python scripts/start_ai.py \
  || echo "[AI] The AI is not ready. The portal still opens; Demo controls shows the AI status and can switch to scripted (no AI)."
exec .venv/bin/python -m streamlit run app.py --server.address localhost
