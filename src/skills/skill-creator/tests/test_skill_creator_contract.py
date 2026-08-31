"""
Contract tests for skill-creator scripts (quick_validate, init_skill, package_skill).
"""

import sys
import subprocess
from pathlib import Path


def test_quick_validate_help():
    script_path = Path(__file__).parent.parent / "scripts" / "quick_validate.py"
    assert script_path.exists(), f"Script {script_path} not found"
    res = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "quick_validate.py" in res.stdout or "usage" in res.stdout.lower()


def test_init_skill_help():
    script_path = Path(__file__).parent.parent / "scripts" / "init_skill.py"
    assert script_path.exists(), f"Script {script_path} not found"
    res = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "init_skill.py" in res.stdout or "usage" in res.stdout.lower()


def test_package_skill_help():
    script_path = Path(__file__).parent.parent / "scripts" / "package_skill.py"
    assert script_path.exists(), f"Script {script_path} not found"
    res = subprocess.run([sys.executable, str(script_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "package_skill.py" in res.stdout or "usage" in res.stdout.lower()
