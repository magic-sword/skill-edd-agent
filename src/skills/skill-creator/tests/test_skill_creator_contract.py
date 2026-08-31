"""
Contract tests for skill-creator meta-skill (structure, templates, and unified CLI integration).
"""

import sys
import subprocess
from pathlib import Path


def test_skill_creator_structure_and_assets():
    skill_dir = Path(__file__).parent.parent
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "references" / "skill_design_guide.md").exists()
    assert (skill_dir / "assets" / "templates" / "workflow_template.md").exists()
    assert (skill_dir / "assets" / "templates" / "task_based_template.md").exists()
    assert (skill_dir / "assets" / "templates" / "reference_template.md").exists()
    assert (skill_dir / "assets" / "templates" / "capabilities_template.md").exists()


def test_skill_creator_cli_contracts():
    # 1. edd init --help
    res = subprocess.run([sys.executable, "-m", "edd_agent_tools.cli", "init", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "--pattern" in res.stdout

    # 2. edd validate --help
    res = subprocess.run([sys.executable, "-m", "edd_agent_tools.cli", "validate", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "validate" in res.stdout.lower()

    # 3. edd package --help
    res = subprocess.run([sys.executable, "-m", "edd_agent_tools.cli", "package", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "package" in res.stdout.lower()
