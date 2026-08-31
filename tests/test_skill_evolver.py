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
    assert evolver_dir.exists()
    assert (evolver_dir / "SKILL.md").exists()
    assert (evolver_dir / "references" / "eval_framework.md").exists()
    assert (evolver_dir / "references" / "tier_promotion.md").exists()

    val_res = SkillValidator.validate_directory(evolver_dir)
    assert val_res.is_valid, f"skill-evolver validation failed: {val_res.errors}"
    assert len(val_res.errors) == 0

    state = SkillsState()
    skill = state.get_skill("skill-evolver")
    assert skill is not None


def test_skill_evolver_workflow_via_unified_cli():
    """skill-evolver のワークフロー（eval, diagnose, optimize）が edd CLI を通じて正常に実行できることを検証"""
    from edd_agent_tools.cli import main as cli_main

    # 1. 評価実行 (eval)
    res_eval = cli_main(["eval", "case-converter", "--type", "contract"])
    assert res_eval == 0

    # 2. 診断実行 (diagnose)
    res_diag = cli_main(["diagnose", "case-converter", "--format", "markdown"])
    assert res_diag == 0

    # 3. 最適化・Tier昇格実行 (optimize)
    res_opt = cli_main(["optimize", "case-converter", "--tier", "1"])
    assert res_opt == 0
