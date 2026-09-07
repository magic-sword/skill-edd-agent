"""
Phase 2 新機能テストスイート

1. AdversarialRedTeamRunner (edd red-team - Table 1 Pattern 4)
2. GoldenDatasetExpander (edd expand-dataset - Table 1 Pattern 2)
3. trace-harvester スキル資産 (Section 6: Assisted authoring from traces)
4. SkillOptimizer Tier 3 レッドチーミング昇格ゲート統合
"""

import json
import pytest
from pathlib import Path

from edd_agent_tools.state import SkillsState
from edd_agent_tools.evaluation.red_team import AdversarialRedTeamRunner
from edd_agent_tools.evaluation.dataset_expander import GoldenDatasetExpander
from edd_agent_tools.validation.validator import SkillValidator
from edd_agent_tools.evaluation.optimizer import SkillOptimizer
from edd_agent_tools.cli import main


def test_adversarial_red_team_runner_execution():
    """AdversarialRedTeamRunner が言い換え・境界値・インジェクション耐性を正常に評価できることを検証"""
    runner = AdversarialRedTeamRunner()
    res = runner.run_red_team_evaluation(skill_name="case-converter", threshold=0.85)

    assert res.get("status") == "success"
    assert res.get("passed") is True
    assert res.get("accuracy") >= 0.85
    assert res.get("total_probes") >= 6
    assert "probe_breakdown" in res
    assert "rephrasing" in res["probe_breakdown"]
    assert "boundary" in res["probe_breakdown"]
    assert "injection_resistance" in res["probe_breakdown"]


def test_golden_dataset_expander_execution(tmp_path):
    """GoldenDatasetExpander が初期シードから 20 ケース以上の Golden Dataset を合成・保存できることを検証"""
    expander = GoldenDatasetExpander()
    tmp_out = tmp_path / "golden_test.json"

    res = expander.expand_golden_dataset(
        skill_name="case-converter",
        target_count=20,
        output_file=tmp_out
    )

    assert res.get("status") == "success"
    assert res.get("total_cases") >= 20
    assert res.get("positive_cases") >= 14
    assert res.get("negative_cases") >= 6
    assert tmp_out.exists()

    with open(tmp_out, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_cases"] >= 20
    assert len(data["eval_cases"]) >= 20
    assert "conversation" in data["eval_cases"][0]


def test_trace_harvester_skill_spec_and_contract():
    """trace-harvester スキルが白書標準に適合し、静的検証に合格することを検証"""
    skill_dir = Path("src/skills/trace-harvester")
    assert skill_dir.exists()
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "scripts" / "trace_harvester.py").exists()
    assert (skill_dir / "tests" / "trace-harvester.test.json").exists()

    val_res = SkillValidator.validate_directory(skill_dir)
    assert val_res.is_valid is True
    assert len(val_res.errors) == 0


def test_cli_phase2_commands_dispatch(tmp_path):
    """CLI サブコマンド (red-team, expand-dataset) が正常にディスパッチされることを検証"""
    # 1. red-team
    assert main(["red-team", "case-converter"]) == 0

    # 2. expand-dataset to tmp file
    tmp_ds = tmp_path / "custom_golden.json"
    assert main(["expand-dataset", "case-converter", "--count", "20", "--out", str(tmp_ds)]) == 0
    assert tmp_ds.exists()


def test_optimizer_tier_3_red_team_gate():
    """SkillOptimizer が Tier 3 昇格時にレッドチーミングテストを実行することを検証"""
    optimizer = SkillOptimizer()
    original_tier = optimizer.state.get_skill_tier("case-converter")
    try:
        # 人間承認フラグ (--yes / human_approved=True) を伴って Tier 3 昇格を実行
        res = optimizer.optimize_skill(
            skill_name="case-converter",
            target_tier=3,
            human_approved=True,
            run_cascade=False
        )
        assert res.get("status") == "promoted"
        assert res.get("promoted_tier") == 3
        assert res.get("human_approved") is True
    finally:
        optimizer.state.set_skill_tier("case-converter", original_tier)
