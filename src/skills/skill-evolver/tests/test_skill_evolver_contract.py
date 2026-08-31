"""
Contract tests for skill-evolver scripts (evolver, diagnoser).
"""

import sys
import subprocess
from pathlib import Path


def test_evolver_help():
    script_path = Path(__file__).parent.parent / "scripts" / "evolver.py"
    assert script_path.exists(), f"Script {script_path} not found"
    res = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "evolver.py" in res.stdout or "usage" in res.stdout.lower()


def test_diagnoser_help():
    script_path = Path(__file__).parent.parent / "scripts" / "diagnoser.py"
    assert script_path.exists(), f"Script {script_path} not found"
    res = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "diagnoser.py" in res.stdout or "usage" in res.stdout.lower()
