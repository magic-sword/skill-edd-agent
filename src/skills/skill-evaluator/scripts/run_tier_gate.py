#!/usr/bin/env python3
"""
Tier 昇格ゲートキーパースクリプト (CLI & API 対応)
Tier 1 (Production), Tier 2 (Verified), Tier 3 (Mastered) の防壁テストを実行し、
合格時に SkillsState に登録・昇格させる。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from edd_agent_tools.skills import SkillsState, SkillTier
from edd_agent_tools.evaluation import ContractTestRunner, SimulationEvalRunner, LocalWorkspaceEnv


def run_tier_gate(
    skill_name: str,
    target_tier: int = 1,
    eval_set_base_path: str = "tests"
) -> Dict[str, Any]:
    """対象スキルの Tier 昇格防壁テストを実行し、合否判定・ステータス更新を行う。"""
    state = SkillsState()
    skill = state.get_skill(skill_name)
    if not skill:
        return {
            "status": "failed",
            "message": f"Skill '{skill_name}' was not found in SkillsState."
        }

    # 1. 依存関係グラフ検証 (DAG Check)
    is_dag_valid, dag_errors = state.validate_dependency_graph()
    if not is_dag_valid:
        return {
            "status": "failed",
            "message": f"Dependency DAG validation failed: {dag_errors}"
        }

    env = LocalWorkspaceEnv()
    base_p = Path(eval_set_base_path)
    skill_tests_dir = Path(skill.root_dir) / "tests"

    def _find_evalset(test_type: str) -> Optional[Path]:
        cand1 = base_p / skill_name / f"{skill_name}_{test_type}.evalset.json"
        cand2 = base_p / f"{skill_name}_{test_type}.evalset.json"
        cand3 = skill_tests_dir / f"{skill_name}_{test_type}.evalset.json"
        for c in [cand1, cand2, cand3]:
            if c.exists():
                return c
        return None

    # Tier 1 判定: 契約テスト(100%) + トリガーテスト(90%)
    if target_tier >= 1:
        contract_f = _find_evalset("contract")
        if contract_f:
            with open(contract_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            c_res = ContractTestRunner().run_tests(skill=skill, test_cases_data=cases, env=env)
            if c_res.failed > 0 or c_res.accuracy < 1.0:
                return {
                    "status": "failed",
                    "message": f"Tier 1 Contract tests failed: {c_res.passed}/{c_res.total} passed."
                }

        trigger_f = _find_evalset("trigger")
        if trigger_f:
            with open(trigger_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            t_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if t_res.accuracy < 0.9:
                return {
                    "status": "failed",
                    "message": f"Tier 1 Trigger test accuracy ({t_res.accuracy:.1%}) is below threshold (90%)."
                }

    # Tier 2 判定: ゴールデンテスト(90%) + ジャッジテスト(85%)
    if target_tier >= 2:
        golden_f = _find_evalset("golden")
        if golden_f:
            with open(golden_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            g_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if g_res.accuracy < 0.9:
                return {
                    "status": "failed",
                    "message": f"Tier 2 Golden test accuracy ({g_res.accuracy:.1%}) is below threshold (90%)."
                }

        judge_f = _find_evalset("judge")
        if judge_f:
            with open(judge_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            j_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if j_res.accuracy < 0.85:
                return {
                    "status": "failed",
                    "message": f"Tier 2 Judge test accuracy ({j_res.accuracy:.1%}) is below threshold (85%)."
                }

    # Tier 3 判定: 推論軌跡テスト + 敵対的テスト(90%)
    if target_tier >= 3:
        trajectory_f = _find_evalset("trajectory")
        if trajectory_f:
            with open(trajectory_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            tr_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if tr_res.accuracy < 0.9:
                return {
                    "status": "failed",
                    "message": f"Tier 3 Trajectory test accuracy ({tr_res.accuracy:.1%}) is below threshold (90%)."
                }

        adversarial_f = _find_evalset("adversarial")
        if adversarial_f:
            with open(adversarial_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            adv_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if adv_res.accuracy < 0.9:
                return {
                    "status": "failed",
                    "message": f"Tier 3 Adversarial test accuracy ({adv_res.accuracy:.1%}) is below threshold (90%)."
                }

    # 合格 ➔ Tier 登録・昇格
    tier_enum = SkillTier(target_tier)
    state.register_skill(skill_name=skill_name, tier=tier_enum)

    return {
        "status": "success",
        "message": f"Skill '{skill_name}' successfully passed all Tier {target_tier} gating tests and is promoted.",
        "skill_name": skill_name,
        "promoted_tier": target_tier
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Tier Gating tests for a skill and promote if passed")
    parser.add_argument("skill_name", help="Name of the skill to evaluate")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier level (1, 2, or 3)")
    parser.add_argument("--eval-dir", default="tests", help="Base directory for evalset files")

    args = parser.parse_args()
    res = run_tier_gate(args.skill_name, target_tier=args.tier, eval_set_base_path=args.eval_dir)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res["status"] == "success" else 1)
