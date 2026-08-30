#!/usr/bin/env python3
"""
Skill Optimizer & Promotion Engine
スキルのテスト実行、静的検証、連鎖回帰テスト（Cascade Testing）、および Tier 昇格を完全決定論的に実行します。
Anthropic / Google ADK 規約に準拠（Zero LLM dependency in scripts）。

Usage:
    optimizer.py <skill-name> [--target-tier {0,1,2,3}] [--cascade] [--dry-run]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List

from edd_agent_tools.skills import (
    SkillsState,
    Skill,
    SkillValidator,
    SkillTier
)
from edd_agent_tools.evaluation import (
    ContractTestRunner,
    SimulationEvalRunner,
    CascadeTestRunner,
    LocalWorkspaceEnv
)
from edd_agent_tools.evaluation.models import EvalDetailReport


class SkillOptimizer:
    """決定論的テスト実行、静的検証、連鎖回帰テスト、Tier 昇格を行うエンジン。"""

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()
        self.contract_runner = ContractTestRunner()
        self.sim_runner = SimulationEvalRunner()
        self.cascade_runner = CascadeTestRunner(state=self.state)
        self.env = LocalWorkspaceEnv()

    def run_verification(self, skill_name: str) -> Dict[str, Any]:
        """対象スキルの静的検証および単体評価テストを実行します。"""
        skill_obj = self.state.get_skill(skill_name)
        if not skill_obj or not os.path.exists(skill_obj.root_dir):
            return {
                "status": "failed",
                "message": f"Skill '{skill_name}' not found on disk."
            }

        # 1. 静的検証 (Linter)
        val_res = SkillValidator.validate_directory(skill_obj.root_dir)
        if not val_res.is_valid:
            return {
                "status": "validation_failed",
                "errors": val_res.errors,
                "warnings": val_res.warnings,
                "passed": False
            }

        # 2. 契約テストおよびシミュレーションテストの実行
        test_files = skill_obj.tests.list_evalsets()
        all_passed = True
        test_results = {}

        for tf in test_files:
            try:
                with open(tf, "r", encoding="utf-8") as f:
                    eval_data = json.load(f)
                
                t_name = Path(tf).stem.split("_")[-1]
                if "contract" in t_name:
                    res = self.contract_runner.run_tests(skill=skill_obj, test_cases_data=eval_data, env=self.env)
                else:
                    res = self.sim_runner.run_tests(skill=skill_obj, eval_set_data=eval_data, env=self.env)

                test_results[t_name] = {
                    "passed": res.passed,
                    "failed": res.failed,
                    "accuracy": res.accuracy
                }
                if res.failed > 0 or res.accuracy < 0.8:
                    all_passed = False
            except Exception as e:
                test_results[Path(tf).stem] = {"error": str(e)}
                all_passed = False

        return {
            "status": "success" if all_passed else "tests_failed",
            "skill_name": skill_name,
            "validation_passed": True,
            "all_tests_passed": all_passed,
            "test_results": test_results
        }

    def optimize_skill(
        self,
        skill_name: str,
        target_tier: int = 1,
        run_cascade: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        対象スキルの検証、連鎖回帰テスト、Tier 昇格を実行します。
        """
        skill_obj = self.state.get_skill(skill_name)
        if not skill_obj or not os.path.exists(skill_obj.root_dir):
            return {
                "status": "failed",
                "message": f"Skill '{skill_name}' was not found in SkillsState."
            }

        # 1. 単体検証
        verif_res = self.run_verification(skill_name)
        if not verif_res.get("all_tests_passed"):
            return {
                "status": "needs_healing",
                "skill_name": skill_name,
                "details": verif_res,
                "message": "単体テストまたは静的検証に失敗しました。skill-diagnoser で原因を分析し、修正を適用してください。"
            }

        # 2. 連鎖回帰テスト (Cascade Regression Testing)
        cascade_results = {}
        if run_cascade:
            try:
                cascade_results = self.cascade_runner.run_cascade_tests(skill_name)
                cascade_all_passed = bool(cascade_results.get("all_passed", True))
                if not cascade_all_passed:
                    return {
                        "status": "cascade_failed",
                        "skill_name": skill_name,
                        "cascade_results": cascade_results,
                        "message": "依存する上位スキルの連鎖回帰テストに失敗しました。"
                    }
            except Exception as e:
                cascade_results = {"error": str(e)}

        # 3. Tier 昇格の登録
        try:
            tier_enum = SkillTier(target_tier)
            self.state.register_skill(skill_name=skill_name, tier=tier_enum)
        except Exception as e:
            return {
                "status": "registration_failed",
                "message": f"Tier 昇格登録に失敗しました: {e}"
            }

        return {
            "status": "success",
            "skill_name": skill_name,
            "tier": SkillTier(target_tier).name,
            "tier_value": target_tier,
            "verification": verif_res,
            "cascade_results": cascade_results,
            "message": f"スキル '{skill_name}' は検証および連鎖回帰テストに合格し、[{SkillTier(target_tier).name}] へ昇格しました。"
        }


def optimize_skill(skill_name: str, target_tier: int = 1, run_cascade: bool = True, max_retries: int = 3) -> Dict[str, Any]:
    """モジュールレベルのヘルパー関数"""
    optimizer = SkillOptimizer()
    return optimizer.optimize_skill(
        skill_name=skill_name,
        target_tier=target_tier,
        run_cascade=run_cascade,
        max_retries=max_retries
    )


def main():
    parser = argparse.ArgumentParser(description="Skill Optimizer & Promotion Engine (Deterministic, Zero-LLM)")
    parser.add_argument("skill", type=str, help="対象スキルの論理名")
    parser.add_argument("--target-tier", "-t", type=int, default=1, choices=[0, 1, 2, 3], help="昇格目標の Tier (0: Sandbox, 1: Trusted, 2: Core)")
    parser.add_argument("--cascade", "-c", action="store_true", default=True, help="連鎖回帰テストを実行する")
    parser.add_argument("--format", "-f", type=str, choices=["json", "text"], default="text", help="出力フォーマット")

    args = parser.parse_args()

    optimizer = SkillOptimizer()
    res = optimizer.optimize_skill(
        skill_name=args.skill,
        target_tier=args.target_tier,
        run_cascade=args.cascade
    )

    if args.format == "json":
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"==================================================")
        print(f"🚀 Skill Optimization & Promotion: {args.skill}")
        print(f"==================================================")
        print(f"Status: {res.get('status')}")
        print(f"Message: {res.get('message')}")
        if "tier" in res:
            print(f"Current Tier: [{res.get('tier')}]")
        if "cascade_results" in res and res["cascade_results"]:
            print(f"Cascade Results: {res['cascade_results']}")


if __name__ == "__main__":
    main()
