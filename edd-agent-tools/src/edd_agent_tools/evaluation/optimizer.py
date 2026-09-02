"""
Evaluation Optimizer & Promotion Engine for edd-agent-tools

スキルの検証、多層評価、pass^k 連続信頼性検査、連鎖回帰テスト（Cascade Testing）、
および Tier 1〜3 昇格（Human Sign-off ゲート対応）を実行する最適化エンジン。
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
from edd_agent_tools.evaluation.co_loaded_runner import CoLoadedEvalRunner
from edd_agent_tools.evaluation.environment import LocalWorkspaceEnv


class SkillOptimizer:
    """決定論的テスト実行、静的検証、pass^k 評価、連鎖回帰テスト、Tier 昇格を行うエンジン。"""

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()
        self.cascade_runner = CascadeTestRunner(state=self.state)
        self.co_loaded_runner = CoLoadedEvalRunner(state=self.state)

    def run_verification(
        self,
        skill_name: str,
        pass_k: int = 1
    ) -> Dict[str, Any]:
        """対象スキルの静的検証および単体評価テストを実行します（pass^k 対応）。"""
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

        # 2. 契約テスト (pass^k 連続実行)
        if skill:
            contract_path_str = skill.tests.get_evalset_path("contract")
            if contract_path_str and os.path.exists(contract_path_str):
                import json
                with open(contract_path_str, "r", encoding="utf-8") as f:
                    cases = json.load(f)
                runner = ContractTestRunner()
                env = LocalWorkspaceEnv(target_files=[str(skill.root_dir)])
                res = runner.run_tests(skill=skill, test_cases_data=cases, env=env, pass_k=pass_k)
                if res.failed > 0:
                    return {
                        "status": "contract_tests_failed",
                        "passed": False,
                        "accuracy": res.accuracy,
                        "failed_count": res.failed,
                        "pass_k": pass_k
                    }


        return {
            "status": "success",
            "skill_name": skill_name,
            "validation_passed": True,
            "all_tests_passed": True,
            "pass_k": pass_k
        }

    def optimize_skill(
        self,
        skill_name: str,
        target_tier: int = 1,
        run_cascade: bool = True,
        pass_k: Optional[int] = None,
        human_approved: bool = False,
        require_signoff: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """対象スキルの検証、連鎖回帰テスト、Tier 昇格を実行します。
        
        Tier 3 (Action-Allowed) への昇格時は、ホワイトペーパー準拠で以下を要求：
        - pass^k >= 3 (持続的一貫性)
        - Human Sign-off (人間承認: human_approved=True)
        """
        # Tier 3 の場合はデフォルト pass_k=3 を適用
        effective_pass_k = pass_k or (3 if target_tier >= 3 else 1)

        # 1. 単体検証 (pass^k 連続実行)
        verif = self.run_verification(skill_name, pass_k=effective_pass_k)
        if not verif.get("all_tests_passed"):
            return {
                "status": "needs_healing",
                "skill_name": skill_name,
                "details": verif,
                "message": "単体テストまたは静的検証に失敗しました。"
            }

        # 2. 連鎖回帰テスト
        if run_cascade and self.cascade_runner:
            cascade_res = self.cascade_runner.run_cascade(skill_name, target_tier=target_tier)
            if not cascade_res.get("all_passed", True):
                return {
                    "status": "cascade_failed",
                    "skill_name": skill_name,
                    "cascade_results": cascade_res,
                    "message": "依存関係の連鎖回帰テストに失敗しました。"
                }

        # 3. Tier 3 (Action-Allowed) 昇格時の Human Sign-off ゲート検査
        if target_tier >= int(SkillTier.ACTION_ALLOWED) and require_signoff and not human_approved:
            return {
                "status": "pending_human_signoff",
                "skill_name": skill_name,
                "target_tier": target_tier,
                "message": "Tier 3 (Action-Allowed) 昇格には人間の明示的承認 (Human Sign-off) が必要です。--yes または human_approved=True を指定してください。"
            }

        # 4. Tier 昇格
        self.state.set_skill_tier(skill_name, SkillTier(target_tier))
        return {
            "status": "promoted",
            "skill_name": skill_name,
            "promoted_tier": target_tier,
            "pass_k": effective_pass_k,
            "human_approved": human_approved if target_tier >= 3 else None,
            "message": f"Skill '{skill_name}' successfully promoted to Tier {target_tier}!"
        }
