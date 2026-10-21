#!/usr/bin/env bash
# Runs all automated tests (no AI model needed, about 2 minutes). In Terminal:   bash run_tests.sh
# Full output saved to logs/test_output.txt
cd "$(dirname "$0")" || exit 1
[ -x .venv/bin/python ] || { echo "Run the setup first:   bash setup.sh"; exit 1; }
mkdir -p logs
.venv/bin/python -m pytest -p no:cacheprovider -v > logs/test_output.txt 2>&1
code=$?
grep -E "passed|failed|error" logs/test_output.txt | tail -3
echo "Full output: logs/test_output.txt"
exit $code
