import pytest
from pathlib import Path
from edd_agent_tools import (
    SkillsState,
    SkillValidator,
    SkillTier
)


def test_skill_evolver_structure_and_validation():
    """skill-evolver スキル自体の静的バリデーションと構造検証"""
    evolver_dir = Path("/workspace/src/skills/skill-evolver")
    val_res = SkillValidator.validate_directory(evolver_dir)
    assert val_res.is_valid, f"skill-evolver validation failed: {val_res.errors}"

    state = SkillsState()
    skill = state.get_skill("skill-evolver")
    assert skill is not None
    assert "evolver.py" in skill.list_scripts()
    assert "diagnoser.py" in skill.list_scripts()


def test_skill_evolver_scripts_execution():
    """skill-evolver 内のスクリプト群の基本動作検証"""
    state = SkillsState()
    skill = state.get_skill("skill-evolver")
    assert skill is not None

    evolver_mod = skill.load_module("evolver.py")
    assert hasattr(evolver_mod, "cmd_eval")
    assert hasattr(evolver_mod, "cmd_diagnose")
    assert hasattr(evolver_mod, "cmd_optimize")

    diag_mod = skill.load_module("diagnoser.py")
    assert hasattr(diag_mod, "extract_failure_context")
    assert hasattr(diag_mod, "format_markdown")
