#!/usr/bin/env bash
# Checks the agent with the real AI model (LLM_PROVIDER in .env, normally the local Ollama model).
# In Terminal:   bash run_live_checks.sh          the 8 main scenarios (S1, S3, S4, S6 in English and Arabic)
#                bash run_live_checks.sh all      all 42 scenarios, the 78 chat probes and the 56 stress conversations
# Each reply takes seconds to a minute depending on the computer, so "all" can take a few hours.
# Reports: docs/05_test_results_<model>.md (full scenario run), logs/scenario_runs, logs/probes and logs/stress
cd "$(dirname "$0")" || exit 1
[ -x .venv/bin/python ] || { echo "Run the setup first:   bash setup.sh"; exit 1; }
.venv/bin/python scripts/start_ai.py || { echo "The AI model is not ready (see above)."; exit 1; }
P=$(.venv/bin/python -c "from agent.config import get_settings; print(get_settings().llm_provider)")
mkdir -p logs
if [ "${1:-}" = "all" ]; then
  .venv/bin/python scripts/run_scenarios.py --provider "$P" | tee logs/live_scenarios.txt
  .venv/bin/python scripts/probe_chat.py --provider "$P" | tee logs/live_probes.txt
  .venv/bin/python scripts/stress_test.py --provider "$P" | tee logs/live_stress.txt
else
  .venv/bin/python scripts/run_scenarios.py --provider "$P" --only S1 S3 S4 S6 S1-AR S3-AR S4-AR S6-AR | tee logs/live_scenarios.txt
fi
