"""
Contract tests for skill-evolver meta-skill (structure, references, and unified CLI integration).
"""

import sys
import subprocess
from pathlib import Path


def test_skill_evolver_structure_and_references():
    skill_dir = Path(__file__).parent.parent
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "references" / "eval_framework.md").exists()
    assert (skill_dir / "references" / "tier_promotion.md").exists()


def test_skill_evolver_cli_contracts():
    # 1. edd eval --help
    res = subprocess.run([sys.executable, "-m", "edd_agent_tools.cli", "eval", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "--type" in res.stdout

    # 2. edd diagnose --help
    res = subprocess.run([sys.executable, "-m", "edd_agent_tools.cli", "diagnose", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "diagnose" in res.stdout.lower()

    # 3. edd optimize --help
    res = subprocess.run([sys.executable, "-m", "edd_agent_tools.cli", "optimize", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "--tier" in res.stdout
