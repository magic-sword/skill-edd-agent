import os
import json
import pytest
from pathlib import Path

from edd_agent_tools import (
    Skill,
    SkillsState,
    SkillValidator,
    SkillTier,
    LocalWorkspaceEnv,
    ContractTestRunner,
    SimulationEvalRunner
)

@pytest.fixture
def temp_skills_dir(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir

def test_e2e_evaluation_and_tier_gating(tmp_path):
    """EDD (Evaluation-Driven Development) に基づく多層評価と Tier 昇格ゲートの E2E 検証"""
    from edd_agent_tools.packaging import SkillScaffolder

    # 1. 雛形スキルの生成
    skill_dir = SkillScaffolder.scaffold("json-schema-validator", output_base_dir=tmp_path, pattern="workflow")
    assert skill_dir is not None
    assert (skill_dir / "SKILL.md").exists()

    skill = Skill(root_dir=str(skill_dir), tier=0)
    assert skill.name == "json-schema-validator"

    # 2. 自動スキャフォールドされた Google ADK 2.0 公式 EvalSet (SSOT) の検証
    tests_dir = skill_dir / "tests"
    ssot_test_file = tests_dir / "json-schema-validator.test.json"
    assert ssot_test_file.exists()
    assert (tests_dir / "test_config.json").exists()

    with open(ssot_test_file, "r", encoding="utf-8") as f:
        ssot_eval_data = json.load(f)

    # 3. ContractTestRunner の実行 (SSOT からの決定論的 Black-box CLI 実行)
    env = LocalWorkspaceEnv(workspace_dir=str(tmp_path))
    c_runner = ContractTestRunner()
    c_res = c_runner.run_tests(skill=skill, test_cases_data=ssot_eval_data, env=env)
    assert c_res.passed > 0
    assert c_res.failed == 0
    assert c_res.accuracy == 1.0

    # 4. SimulationEvalRunner の多層評価実行 (Trigger, Trajectory, Rubric を一括検証)
    s_runner = SimulationEvalRunner()
    sim_res = s_runner.run_tests(skill=skill, eval_set_data=ssot_eval_data, env=env)
    assert sim_res.passed > 0
    assert sim_res.failed == 0
    assert sim_res.accuracy == 1.0

    # 5. Tier 1 昇格の検証
    state_file = tmp_path / "skills_state.json"
    state_file.write_text(f"""{{
      "entries": [{{"path": "{tmp_path.as_posix()}", "name": "tool"}}],
      "inherits": [],
      "exclude": [],
      "skills": {{}},
      "agents": {{}}
    }}""", encoding="utf-8")

    state = SkillsState(state_path=state_file, project_root=tmp_path)
    state.register_skill(skill_name="json-schema-validator", tier=SkillTier.READ_ONLY)
    assert "json-schema-validator" in state.data.skills
    assert state.data.skills["json-schema-validator"].tier == SkillTier.READ_ONLY
