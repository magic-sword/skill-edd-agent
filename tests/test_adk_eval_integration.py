"""
Integration tests for Google ADK 2.0 evaluation features:
- AdkEvalAdapter (Rubrics & Position Swapping)
- Trajectory matching modes (EXACT, IN_ORDER, ANY_ORDER)
- Sustained reliability (pass^k) in ContractTestRunner
- Co-loaded multi-skill benchmark (CoLoadedEvalRunner)
- Human Sign-off gate for Tier 3 promotion in SkillOptimizer
"""

import os
import json
import pytest
from pathlib import Path

from edd_agent_tools import (
    SkillsState,
    SkillTier,
    AdkEvalAdapter,
    SimulationEvalRunner,
    ContractTestRunner,
    CoLoadedEvalRunner,
    SkillOptimizer,
    LocalWorkspaceEnv
)


@pytest.fixture
def test_state():
    return SkillsState()


def test_adk_eval_adapter_deterministic_rubric(test_state):
    """AdkEvalAdapter の決定論的ルーブリック採点と Position Swapping のテスト。"""
    adapter = AdkEvalAdapter(use_position_swapping=True, force_deterministic=True)
    skill = test_state.get_skill("secret-sanitizer")
    assert skill is not None

    rubrics = [
        {"rubric_id": "mask_secrets", "text_property": "The output must mask sensitive credentials."},
        {"rubric_id": "concise", "text_property": "The response must be concise and actionable."}
    ]

    score, details = adapter.evaluate_rubric(
        skill=skill,
        user_input="Please sanitize this API key: sk-1234567890abcdef",
        actual_output="Sanitized output: <API_KEY: ********>",
        rubrics=rubrics,
        reference_output="<API_KEY: ********>"
    )

    assert score >= 0.8
    assert details["rubrics_count"] == 2
    assert details["passed_rubrics"] >= 1
    assert details["mode"] == "deterministic_fallback"


def test_adk_eval_adapter_live_llm_judge(test_state):
    """APIキーが存在する場合の AdkEvalAdapter ネイティブ LLM-as-a-Judge 評価テスト。"""
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        pytest.skip("No Gemini API key available")

    adapter = AdkEvalAdapter(use_position_swapping=True, force_deterministic=False)
    skill = test_state.get_skill("secret-sanitizer")
    rubrics = [
        {"rubric_id": "mask_secrets", "text_property": "The output must mask sensitive credentials."}
    ]

    score, details = adapter.evaluate_rubric(
        skill=skill,
        user_input="Please sanitize this API key: sk-1234567890abcdef",
        actual_output="Sanitized output: <API_KEY: ********>",
        rubrics=rubrics,
        reference_output="<API_KEY: ********>"
    )

    assert score >= 0.5
    assert details["mode"] == "adk_native_llm_judge"


def test_trajectory_modes_adk_compliance(test_state):
    """ADK 3大 Trajectory 評価モード（EXACT / IN_ORDER / ANY_ORDER）の検証。"""
    runner = SimulationEvalRunner()
    skill = test_state.get_skill("secret-sanitizer")

    # ケース 1: EXACT 一致
    case_exact = {
        "cases": [
            {
                "eval_case_id": "t1",
                "intermediate_data": {"tool_uses": [{"name": "secret_sanitizer.py"}]},
                "actual_tool_uses": ["secret_sanitizer.py"]
            }
        ]
    }
    res_exact = runner.run_tests(skill=skill, eval_set_data=case_exact, trajectory_mode="exact")
    assert res_exact.accuracy == 1.0

    # ケース 2: EXACT 不一致（余分なツールや順序違い）
    case_mismatch = {
        "cases": [
            {
                "eval_case_id": "t2",
                "intermediate_data": {"tool_uses": [{"name": "tool_a"}, {"name": "tool_b"}]},
                "actual_tool_uses": ["tool_b", "tool_a"]
            }
        ]
    }
    res_mismatch_exact = runner.run_tests(skill=skill, eval_set_data=case_mismatch, trajectory_mode="exact")
    assert res_mismatch_exact.failed == 1

    # ケース 3: ANY_ORDER では順序不同でも合格
    res_any_order = runner.run_tests(skill=skill, eval_set_data=case_mismatch, trajectory_mode="any_order")
    assert res_any_order.accuracy == 1.0

    # ケース 4: IN_ORDER の部分列テスト
    case_in_order = {
        "cases": [
            {
                "eval_case_id": "t3",
                "intermediate_data": {"tool_uses": [{"name": "step1"}, {"name": "step3"}]},
                "actual_tool_uses": ["step1", "step2", "step3"]
            }
        ]
    }
    res_in_order = runner.run_tests(skill=skill, eval_set_data=case_in_order, trajectory_mode="in_order")
    assert res_in_order.accuracy == 1.0


def test_contract_runner_pass_k(test_state):
    """ContractTestRunner の pass^k 連続実行テスト。"""
    skill = test_state.get_skill("secret-sanitizer")
    assert skill is not None

    contract_file = Path(skill.root_dir) / "tests" / "secret-sanitizer_contract.evalset.json"
    assert contract_file.exists()

    with open(contract_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    runner = ContractTestRunner()
    env = LocalWorkspaceEnv(target_files=["src/skills/secret-sanitizer"])

    # pass^3 実行（3回連続実行で全勝を検証）
    res_k3 = runner.run_tests(skill=skill, test_cases_data=cases, env=env, pass_k=3)
    assert res_k3.failed == 0
    assert res_k3.total == len(cases["eval_cases"]) * 3
    assert res_k3.accuracy == 1.0


def test_co_loaded_multi_skill_benchmark(test_state):
    """CoLoadedEvalRunner の複数スキル共存・干渉テスト。"""
    runner = CoLoadedEvalRunner(state=test_state)
    res = runner.run_co_loaded_evaluation("secret-sanitizer", co_loaded_count=3)

    assert res["status"] == "success"
    assert res["target_skill"] == "secret-sanitizer"
    assert len(res["co_loaded_skills"]) >= 2
    assert res["estimated_context_tokens"] > 0
    assert not res["context_rot_detected"]


def test_human_signoff_gate_tier_3(test_state):
    """Tier 3 (Action-Allowed) 昇格時の Human Sign-off ゲートテスト。"""
    optimizer = SkillOptimizer(state=test_state)

    # 1. 承認なし（human_approved=False）では昇格保留（pending_human_signoff）
    res_pending = optimizer.optimize_skill(
        skill_name="secret-sanitizer",
        target_tier=3,
        run_cascade=False,
        human_approved=False,
        require_signoff=True
    )
    assert res_pending["status"] == "pending_human_signoff"
    assert "Human Sign-off" in res_pending["message"]

    # 2. 承認あり（human_approved=True）では正常に昇格（promoted）
    res_promoted = optimizer.optimize_skill(
        skill_name="secret-sanitizer",
        target_tier=3,
        run_cascade=False,
        human_approved=True,
        require_signoff=True
    )
    assert res_promoted["status"] == "promoted"
    assert res_promoted["promoted_tier"] == 3
