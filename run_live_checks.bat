@echo off
REM Checks the agent with the real AI model (LLM_PROVIDER in .env, normally the local Ollama model).
REM   run_live_checks.bat          the 8 main scenarios (S1, S3, S4, S6 in English and Arabic)
REM   run_live_checks.bat all      all 42 scenarios, the 78 chat probes and the 56 stress conversations
REM Each reply takes seconds to a minute depending on the computer, so "all" can take a few hours.
REM Reports: docs\05_test_results_<model>.md (full scenario run), logs\scenario_runs, logs\probes and logs\stress
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Run setup.bat first. & pause & exit /b 1)
.venv\Scripts\python scripts\start_ai.py || (echo The AI model is not ready ^(see above^). & pause & exit /b 1)
for /f %%p in ('.venv\Scripts\python -c "from agent.config import get_settings; print(get_settings().llm_provider)"') do set "P=%%p"
if not exist logs mkdir logs
if /i "%1"=="all" (
  .venv\Scripts\python scripts\run_scenarios.py --provider %P% > logs\live_scenarios.txt 2>&1
  type logs\live_scenarios.txt
  .venv\Scripts\python scripts\probe_chat.py --provider %P% > logs\live_probes.txt 2>&1
  type logs\live_probes.txt
  .venv\Scripts\python scripts\stress_test.py --provider %P% > logs\live_stress.txt 2>&1
  type logs\live_stress.txt
) else (
  .venv\Scripts\python scripts\run_scenarios.py --provider %P% --only S1 S3 S4 S6 S1-AR S3-AR S4-AR S6-AR > logs\live_scenarios.txt 2>&1
  type logs\live_scenarios.txt
)
pause
