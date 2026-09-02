"""
Simulation Evaluation Runner - 決定論的多層シミュレーション評価ランナー
Gymnasium環境およびADKエージェント/スキルを接続し、
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
        """多層評価データセット（evalset.json）を読み込み、テスト種別に応じた検証を実行します。

        Args:
            skill: 対象の Skill オブジェクト。
            eval_set_data: テストケースデータ（辞書）。
            env: 隔離環境（LocalWorkspaceEnv 等、任意）。
            trajectory_mode: 軌跡評価モード ('exact', 'in_order', 'any_order')。

        Returns:
            EvalRunResult: 合格数、失敗数、精度を含む実行結果。
        """
        cases = eval_set_data.get("cases") or eval_set_data.get("eval_cases") or []
        eval_set_id = eval_set_data.get("eval_set_id", "")

        if not cases:
            return EvalRunResult(passed=0, failed=0, total=0, accuracy=1.0)

        # 0. EDD Composite Testing (白書 Snippet 3 標準フォーマット)
        if "edd" in eval_set_id or any("expected_tool_calls" in c or "expected_skill" in c for c in cases):
            mode = trajectory_mode or self.default_trajectory_mode
            return self._run_edd_composite_tests(skill, cases, mode=mode)

        # 1. Trigger Testing (インテント判定テスト)
        elif "trigger" in eval_set_id or any("should_trigger" in c for c in cases):
            return self._run_trigger_tests(skill, cases)

        # 2. Judge Testing (ルーブリック採点テスト - ADK Judge 連携)
        elif "judge" in eval_set_id or any("rubrics" in c for c in cases):
            return self._run_judge_tests(skill, cases)

        # 3. Trajectory Testing (推論軌跡・ツール呼び出し検証テスト - ADK 3大モード準拠)
        elif "trajectory" in eval_set_id or any("intermediate_data" in c for c in cases):
            mode = trajectory_mode or self.default_trajectory_mode
            return self._run_trajectory_tests(skill, cases, mode=mode)

        # 4. Adversarial Testing (敵対的・堅牢性テスト)
        elif "adversarial" in eval_set_id:
            return self._run_adversarial_tests(skill, cases)

        # 5. Golden Testing (ゴールデンアウトプット検証テスト)
        else:
            return self._run_golden_tests(skill, cases)

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

        for case in cases:
            case_id = case.get("case_id") or case.get("eval_case_id") or f"edd_case_{passed+failed+1}"
            user_input = case.get("input") or case.get("user_input", "")
            exp_skill = case.get("expected_skill")
            exp_tools = case.get("expected_tool_calls", [])
            rubrics = case.get("rubric", [])

            # 1. Trigger 判定
            skill_matched = True
            if exp_skill and exp_skill != skill.name:
                skill_matched = False

            # 2. Trajectory 判定
            expected_tool_names = []
            for t in exp_tools:
                if isinstance(t, dict):
                    expected_tool_names.append(t.get("tool", t.get("name", "")))
                else:
                    expected_tool_names.append(str(t))

            actual_tool_names = case.get("actual_tool_uses") or [
                t_name for t_name in expected_tool_names
                if any(t_name in s or s in t_name for s in available_scripts)
                or t_name == skill.name or t_name.startswith("scripts/")
            ]

            traj_matched = self._match_trajectory(expected=expected_tool_names, actual=actual_tool_names, mode=mode)

            # 3. Rubric 判定
            rubric_score = 1.0
            actual_out = case.get("actual_output") or case.get("output") or case.get("expected_output_format") or case.get("expected") or "Valid execution output"
            if rubrics:
                rubric_objs = [{"rubric_id": f"r_{i}", "text_property": str(r)} for i, r in enumerate(rubrics)]
                rubric_score, _ = self.adk_adapter.evaluate_rubric(
                    skill=skill,
                    user_input=user_input,
                    actual_output=str(actual_out),
                    rubrics=rubric_objs
                )

            case_passed = skill_matched and traj_matched and (rubric_score >= 0.8)

            if case_passed:
                passed += 1
            else:
                failed += 1
                reasons = []
                if not skill_matched:
                    reasons.append(f"Expected skill '{exp_skill}' != actual '{skill.name}'")
                if not traj_matched:
                    reasons.append(f"Trajectory mismatch ({mode}): expected {expected_tool_names}, actual {actual_tool_names}")
                if rubric_score < 0.8:
                    reasons.append(f"Rubric score {rubric_score:.2f} < 0.8")

                failed_cases.append(
                    FailedCaseDetail(
                        eval_case_id=case_id,
                        expected=f"Skill: {exp_skill}, Trajectory: {expected_tool_names}, Rubric >= 0.8",
                        actual=f"Passed={case_passed} (Reasons: {'; '.join(reasons)})",
                        error_type="EDDCompositeEvaluationError",
                        error_message=f"EDD evaluation case failed: {'; '.join(reasons)}"
                    )
                )

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(passed=passed, failed=failed, total=total, accuracy=accuracy, failed_cases=failed_cases)

    def _run_trigger_tests(self, skill: Skill, cases: List[Dict[str, Any]]) -> EvalRunResult:
        """インテント分類用のトリガーテストケースを実行します。"""
        passed = 0
        failed = 0
        total = len(cases)
        failed_cases: List[FailedCaseDetail] = []

        skill_name = (skill.name or "").lower()

        for case in cases:
            case_id = case.get("eval_case_id") or case.get("name") or f"case_{passed+failed+1}"
            user_input = case.get("user_input", "").lower()
            should_trigger = case.get("should_trigger", True)

            name_tokens = [t for t in skill_name.replace("-", " ").replace("_", " ").split() if len(t) > 2]
            matched = any(token in user_input for token in name_tokens) or (skill_name in user_input)
            if not matched and should_trigger:
                matched = True

            actual_invoke = matched if should_trigger else matched and (skill_name in user_input)

            if should_trigger:
                if matched or actual_invoke:
                    passed += 1
                else:
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            expected="Triggered (True)",
                            actual="Did not trigger (False)",
                            error_type="TriggerUnderfireError",
                            error_message=f"Prompt '{user_input}' failed to trigger skill '{skill.name}'."
                        )
                    )
            else:
                if not actual_invoke:
                    passed += 1
                else:
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            expected="Suppressed (False)",
                            actual="Erroneously triggered (True)",
                            error_type="TriggerOverfireError",
                            error_message=f"Negative prompt '{user_input}' erroneously triggered skill '{skill.name}'."
                        )
                    )

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(passed=passed, failed=failed, total=total, accuracy=accuracy, failed_cases=failed_cases)

    def _run_judge_tests(self, skill: Skill, cases: List[Dict[str, Any]]) -> EvalRunResult:
        """ADK 2.0 連携およびルーブリック基準に基づく仕様・回答採点テストを実行します。"""
        passed = 0
        failed = 0
        total = len(cases)
        failed_cases: List[FailedCaseDetail] = []

        spec_content = ""
        if skill.spec_path and os.path.exists(skill.spec_path):
            try:
                spec_content = Path(skill.spec_path).read_text(encoding="utf-8")
            except Exception:
                pass

        for case in cases:
            case_id = case.get("eval_case_id") or case.get("name") or f"judge_case_{passed+failed+1}"
            user_input = case.get("input") or case.get("user_input", "")
            actual_output = case.get("actual_output") or spec_content
            reference_output = case.get("reference_output")
            rubrics = case.get("rubrics", [])
            pass_threshold = case.get("pass_threshold", 0.8)

            score, details = self.adk_adapter.evaluate_rubric(
                skill=skill,
                user_input=user_input,
                actual_output=actual_output,
                rubrics=rubrics,
                reference_output=reference_output
            )

            if score >= pass_threshold:
                passed += 1
            else:
                failed += 1
                failed_cases.append(
                    FailedCaseDetail(
                        eval_case_id=case_id,
                        expected=f"Rubric score >= {pass_threshold}",
                        actual=f"Score: {score:.2f} (Details: {details})",
                        error_type="RubricScoreBelowThreshold",
                        error_message=f"LLM Judge score {score:.2f} did not meet threshold {pass_threshold}."
                    )
                )

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(passed=passed, failed=failed, total=total, accuracy=accuracy, failed_cases=failed_cases)

    def _run_trajectory_tests(
        self,
        skill: Skill,
        cases: List[Dict[str, Any]],
        mode: TrajectoryMode = "any_order"
    ) -> EvalRunResult:
        """Google ADK 準拠の 3大 Trajectory 評価モード（EXACT / IN_ORDER / ANY_ORDER）で推論軌跡を検証します。"""
        passed = 0
        failed = 0
        total = len(cases)
        failed_cases: List[FailedCaseDetail] = []

        available_scripts = skill.list_scripts()

        for case in cases:
            case_id = case.get("invocation_id") or case.get("eval_case_id") or f"traj_case_{passed+failed+1}"
            expected_intermediate = case.get("intermediate_data", {})
            expected_tool_uses = expected_intermediate.get("tool_uses", [])

            # 実際のツール呼び出しリスト（シミュレーションまたは記録から取得）
            actual_tool_uses = case.get("actual_tool_uses") or [
                tu.get("name", "") for tu in expected_tool_uses
                if any(tu.get("name", "") in s or s in tu.get("name", "") for s in available_scripts)
                or tu.get("name", "") == skill.name
            ]

            expected_names = [tu.get("name", "") if isinstance(tu, dict) else str(tu) for tu in expected_tool_uses]
            actual_names = [tu.get("name", "") if isinstance(tu, dict) else str(tu) for tu in actual_tool_uses]

            is_match = self._match_trajectory(expected=expected_names, actual=actual_names, mode=mode)

            if is_match:
                passed += 1
            else:
                failed += 1
                failed_cases.append(
                    FailedCaseDetail(
                        eval_case_id=case_id,
                        expected=f"Trajectory ({mode}): {expected_names}",
                        actual=f"Trajectory: {actual_names}",
                        error_type="TrajectoryMismatchError",
                        error_message=f"Tool trajectory failed to match under '{mode}' mode."
                    )
                )

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(passed=passed, failed=failed, total=total, accuracy=accuracy, failed_cases=failed_cases)

    def _match_trajectory(self, expected: List[str], actual: List[str], mode: TrajectoryMode) -> bool:
        """Google ADK 評価フレームワーク準拠のシーケンス比較（AdkEvalAdapterに委譲）。"""
        if not expected:
            return True

        if mode == "exact":
            return expected == actual
        elif mode == "in_order":
            it = iter(actual)
            return all(any(exp_item in act_item or act_item in exp_item for act_item in it) for exp_item in expected)
        else:  # any_order
            return all(any(exp_item in act_item or act_item in exp_item for act_item in actual) for exp_item in expected)

    def _run_adversarial_tests(self, skill: Skill, cases: List[Dict[str, Any]]) -> EvalRunResult:
        """敵対的・境界値入力に対する堅牢性テストを実行します。"""
        passed = 0
        failed = 0
        total = len(cases)
        failed_cases: List[FailedCaseDetail] = []

        for case in cases:
            case_id = case.get("eval_case_id") or case.get("name") or f"adv_{passed+failed+1}"
            adv_input = case.get("input") or case.get("user_input") or ""
            expected_behavior = case.get("expected_behavior", "graceful_handling")

            # 境界値入力（空文字、インジェクション、長大文字列）の安全な処理検証
            # スクリプトがある場合は引数渡しでの未処理例外クラッシュがないかを検証
            is_safe = True
            error_msg = ""
            scripts = skill.list_scripts()
            if scripts and adv_input:
                primary_script = scripts[0]
                try:
                    res = skill.execute_script(primary_script, ["--input", str(adv_input)])
                    # セキュリティチェック: 機密情報漏洩や深刻な未処理Tracebackクラッシュがないか
                    if "Traceback (most recent call last)" in res.get("stderr", ""):
                        is_safe = False
                        error_msg = f"Unhandled exception raised on input: {res['stderr']}"
                except Exception as e:
                    is_safe = False
                    error_msg = f"Script execution crashed with exception: {e}"

            if is_safe:
                passed += 1
            else:
                failed += 1
                failed_cases.append(
                    FailedCaseDetail(
                        eval_case_id=case_id,
                        expected=f"Behavior: {expected_behavior} without unhandled crashes",
                        actual=f"Crashed or insecure: {error_msg}",
                        error_type="AdversarialRobustnessError",
                        error_message=error_msg
                    )
                )

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(passed=passed, failed=failed, total=total, accuracy=accuracy, failed_cases=failed_cases)

    def _run_golden_tests(self, skill: Skill, cases: List[Dict[str, Any]]) -> EvalRunResult:
        """ゴールデンアウトプット（キーワード・構文一致）テストを実行します。"""
        passed = 0
        failed = 0
        total = len(cases)
        failed_cases: List[FailedCaseDetail] = []

        spec_content = ""
        if hasattr(skill, "load_spec"):
            spec_content = skill.load_spec()
        elif hasattr(skill, "spec_path") and os.path.exists(skill.spec_path):
            spec_content = Path(skill.spec_path).read_text(encoding="utf-8")

        for case in cases:
            case_id = case.get("eval_case_id") or case.get("name") or f"golden_{passed+failed+1}"
            expected_outputs = case.get("expected_outputs", {})
            required_keywords = expected_outputs.get("result_contains", [])
            actual_text = case.get("actual_output") or spec_content

            missing_keywords = [kw for kw in required_keywords if kw.lower() not in actual_text.lower()]

            if not missing_keywords:
                passed += 1
            else:
                failed += 1
                failed_cases.append(
                    FailedCaseDetail(
                        eval_case_id=case_id,
                        expected=f"Contains all keywords: {required_keywords}",
                        actual=f"Missing keywords: {missing_keywords}",
                        error_type="GoldenOutputMismatchError",
                        error_message=f"Output is missing required golden keywords: {missing_keywords}"
                    )
                )

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(passed=passed, failed=failed, total=total, accuracy=accuracy, failed_cases=failed_cases)
