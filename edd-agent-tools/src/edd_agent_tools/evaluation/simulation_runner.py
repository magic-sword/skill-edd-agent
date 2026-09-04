"""
Simulation Evaluation Runner - Google ADK 2.0 Native Adapter

Google ADK 2.0 純正の AgentEvaluator / adk eval パイプラインを直接駆動し、
スキルの公式 EvalSet (*.test.json) および EvalConfig (test_config.json) に基づく
エージェント評価結果を EvalRunResult として一元集計します。
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

from edd_agent_tools.core.entity import Skill
from edd_agent_tools.models import EvalRunResult, FailedCaseDetail, EvalDetailReport
from edd_agent_tools.models.eval import EvalCase
from edd_agent_tools.evaluation.adk_eval import AdkEvalAdapter, is_valid_api_key

TrajectoryMode = Literal["exact", "in_order", "any_order"]


class SimulationEvalRunner:
    """Google ADK 2.0 純正 AgentEvaluator と直結した評価ランナー。"""

    def __init__(
        self,
        default_trajectory_mode: TrajectoryMode = "in_order",
        adk_adapter: Optional[AdkEvalAdapter] = None
    ):
        self.default_trajectory_mode = default_trajectory_mode
        self.adk_adapter = adk_adapter or AdkEvalAdapter()

    def run_tests(
        self,
        skill: Skill,
        eval_set_data: Dict[str, Any],
        env: Any = None,
        trajectory_mode: Optional[TrajectoryMode] = None,
        agent_module: str = "src"
    ) -> EvalRunResult:
        """Google ADK 2.0 純正評価を実行します。

        Args:
            skill: 対象の Skill オブジェクト。
            eval_set_data: テストケースデータ（辞書）。
            env: 隔離環境（任意）。
            trajectory_mode: 軌跡評価モード ('exact', 'in_order', 'any_order')。
            agent_module: 評価対象のエージェントモジュールパス。

        Returns:
            EvalRunResult: 合格数、失敗数、精度を含む実行結果。
        """
        cases = eval_set_data.get("eval_cases") or eval_set_data.get("cases") or []
        total = len(cases)
        if total == 0:
            return EvalRunResult(passed=0, failed=0, total=0, accuracy=1.0)

        # テストファイルパスの解決
        tests_dir = Path(skill.root_dir) / "tests" if hasattr(skill, "root_dir") and skill.root_dir else Path("tests")
        eval_file_candidates = [
            tests_dir / f"{skill.name}.test.json",
            tests_dir / f"{skill.name}_edd.test.json",
        ]
        eval_file = next((p for p in eval_file_candidates if p.exists()), None)
        if not eval_file:
            all_evals = list(tests_dir.glob("*.test.json"))
            eval_file = all_evals[0] if all_evals else None

        config_file = tests_dir / "test_config.json"
        config_path = str(config_file) if config_file.exists() else None

        # ライブ評価フラグ（明示的 live 指定かつ有効な API キーがある場合）
        raw_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        has_valid_key = is_valid_api_key(raw_key)
        is_live = getattr(self.adk_adapter, "live", False) and has_valid_key

        has_simulated_tools = any(
            isinstance(c, dict) and ("actual_tool_uses" in c or "actual_tool_calls" in c)
            for c in cases
        )

        if is_live and eval_file and not has_simulated_tools:
            return self._run_live_adk_eval(
                agent_module=agent_module,
                eval_file=eval_file,
                config_path=config_path,
                total_cases=total
            )

        # オフライン時またはシミュレーション結果検証: テストケースの静的整合性および軌跡・スクリプト健全性を検証
        mode = trajectory_mode or self.default_trajectory_mode
        return self._run_offline_spec_verification(skill, cases, trajectory_mode=mode)

    def _run_live_adk_eval(
        self,
        agent_module: str,
        eval_file: Path,
        config_path: Optional[str],
        total_cases: int
    ) -> EvalRunResult:
        """Google ADK 2.0 純正 AgentEvaluator を非同期実行して結果を集計します。"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                self.adk_adapter.evaluate_with_adk_agent(
                    agent_module=agent_module,
                    eval_dataset_file_path_or_dir=eval_file,
                    config_file_path=config_path,
                    num_runs=1,
                    print_detailed_results=True
                )
            )
            return EvalRunResult(
                passed=total_cases,
                failed=0,
                total=total_cases,
                accuracy=1.0
            )
        except AssertionError as ae:
            # ADK AgentEvaluator のアサーション失敗
            error_str = str(ae)
            failed_cases = [
                FailedCaseDetail(
                    eval_case_id="adk_eval_failure",
                    expected="All ADK 2.0 criteria satisfied (trajectory, response, rubrics)",
                    actual=error_str,
                    error_type="ADKEvalAssertionError",
                    error_message=error_str
                )
            ]
            return EvalRunResult(
                passed=0,
                failed=total_cases,
                total=total_cases,
                accuracy=0.0,
                failed_cases=failed_cases
            )
        except Exception as e:
            failed_cases = [
                FailedCaseDetail(
                    eval_case_id="adk_eval_error",
                    expected="Successful ADK evaluation pipeline run",
                    actual=str(e),
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
            ]
            return EvalRunResult(
                passed=0,
                failed=total_cases,
                total=total_cases,
                accuracy=0.0,
                failed_cases=failed_cases
            )

    def _run_offline_spec_verification(
        self,
        skill: Skill,
        cases: List[Dict[str, Any]],
        trajectory_mode: TrajectoryMode = "in_order"
    ) -> EvalRunResult:
        """テストケースの整合性、シミュレーション軌跡、およびスクリプト実在性を検証します。"""
        passed = 0
        failed = 0
        total = len(cases)
        failed_cases: List[FailedCaseDetail] = []
        available_scripts = skill.list_scripts()

        for c_idx, raw_case in enumerate(cases, 1):
            case = raw_case if isinstance(raw_case, EvalCase) else EvalCase.model_validate(raw_case)
            case_id = case.eval_case_id or f"case_{c_idx}"
            exp_tools = case.expected_tool_calls

            # 1. 実際のシミュレーションツール呼び出し履歴が存在する場合: ADK TrajectoryEvaluator で判定
            actual_tools = None
            if isinstance(raw_case, dict):
                actual_tools = raw_case.get("actual_tool_uses") or raw_case.get("actual_tool_calls")
            elif hasattr(case, "actual_tool_uses"):
                actual_tools = getattr(case, "actual_tool_uses")

            if actual_tools is not None:
                traj_passed, traj_msg = self.adk_adapter.evaluate_trajectory(
                    actual_tool_calls=actual_tools,
                    expected_tool_calls=exp_tools or [],
                    mode=trajectory_mode,
                    skill_name=skill.name
                )
                if not traj_passed:
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            expected=f"Trajectory match ({trajectory_mode}): {exp_tools}",
                            actual=str(actual_tools),
                            error_type="TrajectoryMismatchError",
                            error_message=traj_msg
                        )
                    )
                    continue

            # 2. スクリプト実在性の検証
            missing_script = None
            if exp_tools:
                for tc in exp_tools:
                    t_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                    t_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                    if t_name == "run_skill_script" and isinstance(t_args, dict):
                        f_path = t_args.get("file_path", "")
                        script_base = Path(f_path).name
                        if script_base and available_scripts and script_base not in available_scripts:
                            missing_script = f_path
                            break
                    elif t_name.startswith("scripts/") or t_name.endswith(".py"):
                        script_base = Path(t_name).name
                        if script_base and available_scripts and script_base not in available_scripts:
                            missing_script = t_name
                            break

            if missing_script:
                failed += 1
                failed_cases.append(
                    FailedCaseDetail(
                        eval_case_id=case_id,
                        expected=f"Referenced script '{missing_script}' exists in {skill.name}/scripts",
                        actual="Script not found",
                        error_type="MissingSkillScriptError",
                        error_message=f"Script '{missing_script}' is referenced in eval case but does not exist."
                    )
                )
            else:
                passed += 1

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(
            passed=passed,
            failed=failed,
            total=total,
            accuracy=accuracy,
            failed_cases=failed_cases
        )
