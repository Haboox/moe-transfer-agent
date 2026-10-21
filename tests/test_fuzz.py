"""Seeded random conversations (scripts/fuzz_chat.py): no crash and no reply problem in 40 conversations."""
import subprocess
import sys
from pathlib import Path


def test_random_conversations_in_both_languages_have_no_problems():
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, str(root / "scripts" / "fuzz_chat.py"), "40"], capture_output=True, text=True,
                       timeout=600, cwd=root)
    assert r.returncode == 0 and "crashes 0 problems 0" in r.stdout, r.stdout[-2000:] + r.stderr[-2000:]
