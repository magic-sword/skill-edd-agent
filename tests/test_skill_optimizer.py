import pytest
from pathlib import Path
from edd_agent_tools.skills import (
    SkillsState,
    SkillValidator,
    SkillTier
)


def test_skill_optimizer_structure_and_validation():
    """skill-optimizer スキル自体の静的バリデーションと依存グラフの検証"""
    optimizer_dir = Path("/workspace/src/skills/skill-optimizer")
    val_res = SkillValidator.validate_directory(optimizer_dir)
    assert val_res.is_valid, f"skill-optimizer validation failed: {val_res.errors}"

    state = SkillsState()
    skill = state.get_skill("skill-optimizer")
    assert skill is not None
    assert "skill-diagnoser" in skill.dependencies
    assert "skill-evaluator" in skill.dependencies

    # DAG整合性
    is_valid, errors = state.validate_dependency_graph()
    assert is_valid, f"Dependency graph errors: {errors}"


def test_skill_optimizer_execution_mock():
    """skill-optimizer の実行ロジックのインスタンス化と基本動作の検証"""
    state = SkillsState()
    skill = state.get_skill("skill-optimizer")
    assert skill is not None

    mod = skill.load_module("optimizer.py")
    assert hasattr(mod, "SkillOptimizer")
    assert hasattr(mod, "optimize_skill")

    optimizer = mod.SkillOptimizer(state=state)
    assert optimizer.cascade_runner is not None

    # 存在しないスキルの場合は failed となること
    res = optimizer.optimize_skill("non-existent-skill-xyz", max_retries=1)
    assert res["status"] == "failed"
