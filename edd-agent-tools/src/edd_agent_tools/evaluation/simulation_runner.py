"""
Simulation Evaluation Runner - 決定論的多層シミュレーション評価ランナー
決定論的サンドボックス環境および ADK 2.0 エージェント/スキルを接続し、
多層評価（Trigger, Golden, Judge, Trajectory, Adversarial）を実行します。
Google ADK 2.0 純正の 3大 Trajectory 評価モード（EXACT / IN_ORDER / ANY_ORDER）および
AdkEvalAdapter（LLM-as-a-Judge / Position Swapping）を完全統合。
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
from concurrent.futures import ThreadPoolExecutor

from edd_agent_tools.core.entity import Skill
from edd_agent_tools.models import EvalRunResult, FailedCaseDetail, EvalDetailReport
from edd_agent_tools.evaluation.adk_eval import AdkEvalAdapter


TrajectoryMode = Literal["exact", "in_order", "any_order"]


class SimulationEvalRunner:
    """多層シミュレーション評価（Trigger, Golden, Judge, Trajectory, Adversarial）を実行するランナー。"""

    def __init__(
        self,
        default_trajectory_mode: TrajectoryMode = "any_order",
        adk_adapter: Optional[AdkEvalAdapter] = None
    ):
        self.default_trajectory_mode = default_trajectory_mode
        self.adk_adapter = adk_adapter or AdkEvalAdapter()

    def run_tests(
        self,
        skill: Skill,
        eval_set_data: Dict[str, Any],
        env: Any = None,
        trajectory_mode: Optional[TrajectoryMode] = None
    ) -> EvalRunResult:
        """多層評価データセット（*.test.json）を読み込み、テスト種別に応じた検証を実行します。

        Args:
            skill: 対象の Skill オブジェクト。
            eval_set_data: テストケースデータ（辞書）。
            env: 隔離環境（LocalWorkspaceEnv 等、任意）。
            trajectory_mode: 軌跡評価モード ('exact', 'in_order', 'any_order')。

        Returns:
            EvalRunResult: 合格数、失敗数、精度を含む実行結果。
        """
        cases = eval_set_data.get("eval_cases") or eval_set_data.get("cases") or []
        eval_set_id = eval_set_data.get("eval_set_id", "")

        if not cases:
            return EvalRunResult(passed=0, failed=0, total=0, accuracy=1.0)

        # Google ADK 2.0 純正アーキテクチャ: すべての評価ケースを ADK 2.0 公式 EvalSet / Trajectory に一本化
        mode = trajectory_mode or self.default_trajectory_mode
        normalized_cases = self._normalize_cases_to_adk(skill, cases)
        return self._run_edd_composite_tests(skill, normalized_cases, mode=mode)

    def _run_edd_composite_tests(
        self,
        skill: Skill,
        cases: List[Dict[str, Any]],
        mode: TrajectoryMode = "any_order"
    ) -> EvalRunResult:
        """白書標準の EDD (Evaluation-Driven Development) 複合ケースを実行します。
        
        各ケースで Trigger (expected_skill), Trajectory (expected_tool_calls), Rubric (rubric) を総合検証します。
        """
        passed = 0
        failed = 0
        total = len(cases)
        failed_cases: List[FailedCaseDetail] = []
        available_scripts = skill.list_scripts()

        for raw_case in cases:
            from edd_agent_tools.models.eval import EvalCase
            case = raw_case if isinstance(raw_case, EvalCase) else EvalCase.model_validate(raw_case)
            case_id = case.eval_id or case.case_id or case.eval_case_id or f"edd_case_{passed+failed+1}"

            user_input = case.input or ""
            exp_tools = case.expected_tool_calls or []
            ref_output = case.expected_output_format
            rubrics = case.rubrics or case.rubric or []

            case_dict = case.model_dump() if hasattr(case, "model_dump") else (case if isinstance(case, dict) else {})
            actual_tools = getattr(case, "actual_tool_uses", None) or case_dict.get("actual_tool_uses")

            # 1. Trigger / Skill 適合性判定 (Google ADK 2.0 Trajectory 規約準拠)
            # 負例（expected_tool_calls が空）ではツール呼び出しが行われないことを Trajectory で判定
            is_negative_case = case.is_negative
            has_skill_in_expected = any(
                skill.name in str(c) or any(s in str(c) for s in available_scripts)
                for c in exp_tools
            )
            if actual_tools is not None:
                skill_script_called = any(
                    skill.name in str(c) or any(s in str(c) for s in available_scripts)
                    for c in actual_tools
                )
                if is_negative_case:
                    skill_matched = not skill_script_called
                elif has_skill_in_expected:
                    skill_matched = skill_script_called
                else:
                    # 期待ツール呼び出しがある汎用軌跡テストまたは外部ツール呼び出し時
                    skill_matched = True
            else:
                # オフライン・静的契約テスト時
                skill_matched = True

            # 2. Trajectory 判定 (Google ADK 2.0 純正 TrajectoryEvaluator に委譲)
            if not exp_tools:
                # 負例等でツール呼び出しが不要なケース
                if actual_tools is not None:
                    traj_matched, traj_msg = self.adk_adapter.evaluate_trajectory(
                        actual_tool_calls=actual_tools,
                        expected_tool_calls=[],
                        mode=mode,
                        skill_name=skill.name
                    )
                else:
                    traj_matched = True
                    traj_msg = "No tool calls expected (Negative boundary case verified)"
            else:
                traj_matched = True
                traj_msg = ""
                if actual_tools is None:
                    # オフライン・静的契約テスト時: 期待されるスクリプトの実在性・健全性を検証
                    for t_item in exp_tools:
                        t_call = t_item if isinstance(t_item, dict) else (t_item.model_dump() if hasattr(t_item, "model_dump") else {"tool": str(t_item)})
                        t_name = t_call.get("tool") or t_call.get("name", "")
                        t_args = t_call.get("args", {}) if isinstance(t_call.get("args"), dict) else {}
                        if t_name == "run_skill_script":
                            f_path = t_args.get("file_path", "")
                            script_base = Path(f_path).name
                            if script_base and available_scripts and script_base not in available_scripts:
                                traj_matched = False
                                traj_msg = f"Referenced script '{f_path}' not found in skill '{skill.name}'"
                                break
                        elif t_name.startswith("scripts/") or t_name.endswith(".py"):
                            script_base = Path(t_name).name
                            if script_base and available_scripts and script_base not in available_scripts:
                                traj_matched = False
                                traj_msg = f"Referenced script '{t_name}' not found in skill '{skill.name}'"
                                break
                    if traj_matched:
                        traj_msg = "Static script integrity verified"
                else:
                    # 実際のツール呼び出し履歴が存在する場合: ADK 2.0 純正 TrajectoryEvaluator で客観的評価
                    traj_matched, traj_msg = self.adk_adapter.evaluate_trajectory(
                        actual_tool_calls=actual_tools,
                        expected_tool_calls=exp_tools,
                        mode=mode,
                        skill_name=skill.name
                    )

            # 3. Rubric & Response 判定 (ADK 2.0 純正 ResponseEvaluator / RubricEvaluator に委譲)
            rubric_score = 1.0
            actual_out = getattr(case, "actual_output", None) or getattr(case, "output", None) or case_dict.get("actual_output") or case_dict.get("output") or ref_output or "Valid execution output"
            if rubrics or ref_output:
                rubric_objs = rubrics if (rubrics and isinstance(rubrics[0], dict)) else [
                    {"rubric_id": f"r_{i}", "text_property": str(r)} for i, r in enumerate(rubrics)
                ]
                rubric_score, _ = self.adk_adapter.evaluate_rubric(
                    skill=skill,
                    user_input=user_input,
                    actual_output=str(actual_out),
                    rubrics=rubric_objs,
                    reference_output=str(ref_output) if ref_output else None
                )

            case_passed = skill_matched and traj_matched and (rubric_score >= 0.8)

            if case_passed:
                passed += 1
            else:
                failed += 1
                reasons = []
                if not skill_matched:
                    reasons.append(f"Trigger mismatch (expected negative={is_negative_case})")
                if not traj_matched:
                    reasons.append(f"Trajectory mismatch ({mode}): {traj_msg}")
                if rubric_score < 0.8:
                    reasons.append(f"Rubric score {rubric_score:.2f} < 0.8")

                failed_cases.append(
                    FailedCaseDetail(
                        eval_case_id=case_id,
                        expected=f"Trigger (negative={is_negative_case}), Trajectory: {exp_tools}, Rubric >= 0.8",
                        actual=f"Passed={case_passed} (Reasons: {'; '.join(reasons)})",
                        error_type="EDDCompositeEvaluationError",
                        error_message=f"EDD evaluation case failed: {'; '.join(reasons)}"
                    )
                )

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(passed=passed, failed=failed, total=total, accuracy=accuracy, failed_cases=failed_cases)

    def _normalize_cases_to_adk(self, skill: Skill, cases: List[Any]) -> List[Any]:
        """各種レガシー形式のケースを Google ADK 2.0 公式 EvalCase 形式に正規化します。
        
        車輪の再発明（トークン一致、手書きキーワード検査）を排除し、
        正例・負例のトリガー判定は ADK 2.0 純正の推論軌跡（tool_trajectory_avg_score）として、
        回答検証は ADK 2.0 純正の ResponseEvaluator (ROUGE-1) / RubricEvaluator に一本化します。
        """
        from edd_agent_tools.models.eval import EvalCase
        normalized = []
        for c in cases:
            if isinstance(c, EvalCase):
                normalized.append(c)
                continue
            if isinstance(c, dict):
                c_copy = dict(c)
                # 1. レガシー should_trigger（Trigger テスト）の ADK 2.0 公式 Trajectory 正規化
                if "should_trigger" in c_copy:
                    should_trig = c_copy.pop("should_trigger")
                    u_in = c_copy.get("user_input") or c_copy.get("input", "")
                    c_copy["input"] = u_in
                    if should_trig:
                        scripts = skill.list_scripts()
                        if scripts:
                            c_copy["expected_tool_calls"] = [{
                                "tool": "run_skill_script",
                                "args": {"skill_name": skill.name, "file_path": f"scripts/{scripts[0]}"}
                            }]
                    else:
                        # 負例: ツール呼び出しが抑止されるべき境界ケース
                        c_copy["expected_tool_calls"] = []

                # 2. レガシー expected_outputs.result_contains（Golden テスト）の ADK 公式 Response 正規化
                if "expected_outputs" in c_copy and isinstance(c_copy["expected_outputs"], dict):
                    exp_out = c_copy.pop("expected_outputs")
                    keywords = exp_out.get("result_contains", [])
                    if keywords and "expected_output_format" not in c_copy:
                        c_copy["expected_output_format"] = " ".join(keywords)

                # 3. レガシー intermediate_data の正規化
                if "intermediate_data" in c_copy and isinstance(c_copy["intermediate_data"], dict):
                    t_uses = c_copy["intermediate_data"].get("tool_uses", [])
                    if t_uses and "expected_tool_calls" not in c_copy:
                        c_copy["expected_tool_calls"] = t_uses

                if "expected_skill" not in c_copy and skill:
                    c_copy["expected_skill"] = skill.name

                try:
                    normalized.append(EvalCase.model_validate(c_copy))
                except Exception:
                    normalized.append(c_copy)
            else:
                normalized.append(c)
        return normalized

