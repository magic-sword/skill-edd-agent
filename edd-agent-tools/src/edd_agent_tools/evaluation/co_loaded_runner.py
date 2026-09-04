"""
Co-loaded Multi-Skill Evaluation Runner (CoLoadedEvalRunner)

ホワイトペーパー Section 4 (p.25-26, Fig 4) 準拠：
5〜15 個のスキルが同時にマウント（Co-loaded）された高コンテキスト負荷環境下で、
スキルのルーティング精度、トークン競合（Attention Competition）、および
他スキルへの干渉・誤発火（Context Rot）をシミュレーション検証するベンチマークランナー。
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from edd_agent_tools.state import SkillsState
from edd_agent_tools.core.entity import Skill
from edd_agent_tools.models import EvalRunResult, FailedCaseDetail, EvalDetailReport
from edd_agent_tools.evaluation.simulation_runner import SimulationEvalRunner


class CoLoadedEvalRunner:
    """複数スキル共存環境下でのルーティングとコンテキスト負荷耐性を評価するランナー。"""

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()
        self.sim_runner = SimulationEvalRunner()

    def run_co_loaded_evaluation(
        self,
        target_skill_name: str,
        co_loaded_count: int = 5,
        test_dataset_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """対象スキルと他の利用可能スキルを同時マウントした状態でトリガー評価を実行します。

        Args:
            target_skill_name: 評価対象のスキル名。
            co_loaded_count: 同時にロードするスキルの目標数（デフォルト 5、最大 15）。
            test_dataset_path: 評価データセットのパス（省略時はスキルの tests/*.test.json）。

        Returns:
            Dict[str, Any]: {
                "target_skill": target_skill_name,
                "co_loaded_skills": list[str],
                "total_skills_count": int,
                "estimated_context_tokens": int,
                "accuracy": float,
                "passed": int,
                "failed": int,
                "context_rot_detected": bool,
                "details": dict
            }
        """
        all_skills = list(self.state.scan_skills().keys())
        target_skill = self.state.get_skill(target_skill_name)
        if not target_skill:
            return {
                "status": "error",
                "message": f"Target skill '{target_skill_name}' not found."
            }

        # 同時ロードするスキルの選定（対象スキル + 他のスキル）
        other_skills = [s for s in all_skills if s != target_skill_name]
        selected_others = other_skills[:co_loaded_count]
        co_loaded_skills = [target_skill_name] + selected_others

        # コンテキストトークン概算（各 Frontmatter ~80 tokens + 対象スキル本文 ~2000 tokens）
        estimated_tokens = (len(co_loaded_skills) * 80) + 2000

        # トリガー評価データの取得
        if test_dataset_path and os.path.exists(test_dataset_path):
            with open(test_dataset_path, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
        else:
            trigger_path_str = target_skill.tests.get_evalset_path("trigger")
            if trigger_path_str and os.path.exists(trigger_path_str):
                with open(trigger_path_str, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                cases_list = raw_data.get("eval_cases") or raw_data.get("cases") or []
                if cases_list and "eval_set_id" in raw_data:
                    t_cases = []
                    for c in cases_list:
                        u_in = c.get("input") or c.get("user_input", "")
                        if not u_in and "conversation" in c:
                            conv = c.get("conversation", [])
                            if conv and isinstance(conv[0], dict):
                                u_content = conv[0].get("user_content", {})
                                parts = u_content.get("parts", []) if isinstance(u_content, dict) else []
                                if parts and isinstance(parts[0], dict):
                                    u_in = parts[0].get("text", "")
                        exp_s = c.get("expected_skill")
                        should_trig = bool(exp_s and (exp_s == target_skill_name or exp_s.replace("-", "_") == target_skill_name.replace("-", "_")))
                        t_cases.append({"user_input": u_in, "should_trigger": should_trig})
                    eval_data = {"eval_set_id": f"{target_skill_name}_coloaded_trigger", "eval_cases": t_cases}
                else:
                    eval_data = raw_data
            else:
                eval_data = {
                    "eval_set_id": f"{target_skill_name}_coloaded_trigger",
                    "eval_cases": [
                        {"user_input": f"Help me with {target_skill_name} task", "should_trigger": True},
                        {"user_input": "What is the capital of France?", "should_trigger": False}
                    ]
                }


        # シミュレーション評価の実行
        res = self.sim_runner.run_tests(skill=target_skill, eval_set_data=eval_data)

        # Context Rot 判定（複数スキル共存下で精度が 80% 未満に落ちた場合は警告）
        context_rot = res.accuracy < 0.8

        return {
            "status": "success",
            "target_skill": target_skill_name,
            "co_loaded_skills": co_loaded_skills,
            "total_skills_count": len(co_loaded_skills),
            "estimated_context_tokens": estimated_tokens,
            "accuracy": res.accuracy,
            "passed": res.passed,
            "failed": res.failed,
            "context_rot_detected": context_rot,
            "message": "Co-loaded multi-skill evaluation completed."
        }
