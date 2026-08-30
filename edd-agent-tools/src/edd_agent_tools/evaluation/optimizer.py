"""
Evaluation Optimizer & Promotion Engine for edd-agent-tools

スキルの検証、連鎖回帰テスト（Cascade Testing）、および Tier 昇格を実行する最適化エンジン。
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from edd_agent_tools.state import SkillsState
from edd_agent_tools.models import SkillTier
from edd_agent_tools.validation.validator import SkillValidator
from edd_agent_tools.evaluation.test_runner import ContractTestRunner
from edd_agent_tools.evaluation.simulation_runner import SimulationEvalRunner
from edd_agent_tools.evaluation.cascade_runner import CascadeTestRunner
from edd_agent_tools.evaluation.environment import LocalWorkspaceEnv


class SkillOptimizer:
    """決定論的テスト実行、静的検証、連鎖回帰テスト、Tier 昇格を行うエンジン。"""

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()
        self.cascade_runner = CascadeTestRunner(state=self.state)

    def run_verification(self, skill_name: str) -> Dict[str, Any]:
        """対象スキルの静的検証および単体評価テストを実行します。"""
        skill = self.state.get_skill(skill_name)
        if not skill:
            cand = Path("src/skills") / skill_name
            if cand.exists():
                skill_dir = cand
            else:
                return {"status": "failed", "message": f"Skill '{skill_name}' not found."}
        else:
            skill_dir = Path(skill.root_dir)

        # 1. 静的検証
        val_res = SkillValidator.validate_directory(skill_dir)
        if not val_res.is_valid:
            return {
                "status": "validation_failed",
                "errors": val_res.errors,
                "warnings": val_res.warnings,
                "passed": False
            }

        # 2. 契約テスト
        if skill:
            contract_file = skill_dir / "tests" / f"{skill_name}_contract.evalset.json"
            if contract_file.exists():
                import json
                with open(contract_file, "r", encoding="utf-8") as f:
                    cases = json.load(f)
                runner = ContractTestRunner()
                env = LocalWorkspaceEnv()
                res = runner.run_tests(skill=skill, test_cases_data=cases, env=env)
                if res.failed > 0:
                    return {
                        "status": "contract_tests_failed",
                        "passed": False,
                        "accuracy": res.accuracy,
                        "failed_count": res.failed
                    }

        return {
            "status": "success",
            "skill_name": skill_name,
            "validation_passed": True,
            "all_tests_passed": True
        }

    def optimize_skill(
        self,
        skill_name: str,
        target_tier: int = 1,
        run_cascade: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """対象スキルの検証、連鎖回帰テスト、Tier 昇格を実行します。"""
        verif = self.run_verification(skill_name)
        if not verif.get("all_tests_passed"):
            return {
                "status": "needs_healing",
                "skill_name": skill_name,
                "details": verif,
                "message": "単体テストまたは静的検証に失敗しました。"
            }

        # 連鎖回帰テスト
        if run_cascade and self.cascade_runner:
            cascade_res = self.cascade_runner.run_cascade(skill_name, target_tier=target_tier)
            if not cascade_res.get("all_passed", True):
                return {
                    "status": "cascade_failed",
                    "skill_name": skill_name,
                    "cascade_results": cascade_res,
                    "message": "依存関係の連鎖回帰テストに失敗しました。"
                }

        # Tier 昇格
        self.state.set_skill_tier(skill_name, SkillTier(target_tier))
        return {
            "status": "promoted",
            "skill_name": skill_name,
            "promoted_tier": target_tier,
            "message": f"Skill '{skill_name}' successfully promoted to Tier {target_tier}!"
        }
