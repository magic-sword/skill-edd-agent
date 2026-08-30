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
    from edd_agent_tools.skills.cli import init_skill

    # 1. 雛形スキルの生成
    skill_dir = init_skill("json-schema-validator", path=str(tmp_path), pattern="workflow")
    assert skill_dir is not None
    assert (skill_dir / "SKILL.md").exists()

    skill = Skill(root_dir=str(skill_dir), tier=0)
    assert skill.name == "json-schema-validator"

    # 2. テストケースの準備 (contract, trigger, trajectory)
    tests_dir = skill_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    contract_data = {
        "eval_set_id": "json_schema_contract",
        "eval_cases": [
            {
                "eval_case_id": "test_help",
                "script_name": "scripts/json_schema_validator.py",
                "cli_args": ["--help"],
                "expected_exit_code": 0,
                "expected_stdout_contains": ["--help"]
            }
        ]
    }
    (tests_dir / "json-schema-validator_contract.evalset.json").write_text(
        json.dumps(contract_data, indent=2), encoding="utf-8"
    )

    trigger_data = {
        "eval_set_id": "json_schema_trigger",
        "cases": [
            {
                "name": "pos_1",
                "user_input": "Validate this JSON against schema",
                "expected_tools": ["json-schema-validator"],
                "should_trigger": True
            }
        ]
    }
    (tests_dir / "json-schema-validator_trigger.evalset.json").write_text(
        json.dumps(trigger_data, indent=2), encoding="utf-8"
    )

    trajectory_data = {
        "eval_set_id": "json_schema_trajectory",
        "cases": [
            {
                "invocation_id": "inv_001",
                "user_content": {"text": "Validate json"},
                "intermediate_data": {
                    "tool_uses": [
                        {"name": "json_schema_validator.py", "args": {"input_val": "sample"}}
                    ]
                }
            }
        ]
    }
    (tests_dir / "json-schema-validator_trajectory.evalset.json").write_text(
        json.dumps(trajectory_data, indent=2), encoding="utf-8"
    )

    # 3. ContractTestRunner の実行
    env = LocalWorkspaceEnv()
    c_runner = ContractTestRunner()
    c_res = c_runner.run_tests(skill=skill, test_cases_data=contract_data, env=env)
    assert c_res.passed == 1
    assert c_res.failed == 0
    assert c_res.accuracy == 1.0

    # 4. SimulationEvalRunner の多層評価実行
    s_runner = SimulationEvalRunner()
    t_res = s_runner.run_tests(skill=skill, eval_set_data=trigger_data, env=env)
    assert t_res.accuracy >= 0.8

    traj_res = s_runner.run_tests(skill=skill, eval_set_data=trajectory_data, env=env)
    assert traj_res.accuracy == 1.0

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
