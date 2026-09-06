"""
Contract Test Runner for edd-agent-tools

スキルの CLI 規約（--help, 引数, 終了コード, 出力）をサンドボックス（LocalWorkspaceEnv 等）内で
決定論的に Black-box 実行・検証するテストランナー。
ホワイトペーパー Section 4 準拠の pass^k（Sustained Reliability）連続実行をサポート。
"""

import os
import sys
import json
import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from edd_agent_tools.core.entity import Skill
from edd_agent_tools.core.protocols import WorkspaceEnvProtocol
from edd_agent_tools.models.eval import EvalCase, EvalCaseSet, FailedCaseDetail, EvalRunResult, EvalDetailReport


class ContractTestRunner:
    """
    スキルの仕様（SKILL.md）および CLI 規約（--help, 引数, 終了コード, 出力）に基づき、
    テストケースデータ（JSON）を用いて決定論的かつ隔離環境下で契約テストを実行するクラス。
    Google ADK 2.0 公式の CodeExecutor 基盤と完全統合され、本番エージェントと同一の環境でテストします。
    """

    def __init__(self, code_executor: Optional[Any] = None):
        if code_executor is not None:
            self.code_executor = code_executor
        else:
            try:
                from edd_agent_tools.adk.executor import LocalSubprocessCodeExecutor
                self.code_executor = LocalSubprocessCodeExecutor()
            except ImportError:
                self.code_executor = None

    def run_tests(
        self,
        skill: Skill,
        test_cases_data: Dict[str, Any] | EvalCaseSet,
        env: WorkspaceEnvProtocol,
        timeout_seconds: int = 180,
        pass_k: int = 1,
        code_executor: Optional[Any] = None
    ) -> EvalRunResult:
        """
        指定されたテストケースデータに基づいて、スキルの CLI 契約テストを実行します。
        pass_k > 1 の場合、全ケースを k 回連続実行し、全勝（Sustained pass^k）を検証します。

        Args:
            skill: テスト対象の Skill オブジェクト。
            test_cases_data: テストケースデータ辞書（eval_cases を含む）または EvalCaseSet オブジェクト。
            env: 隔離環境オブジェクト（WorkspaceEnvProtocol）。
            timeout_seconds: タイムアウト秒数。
            pass_k: 連続実行回数（持続的信頼性指標）。
            code_executor: 実行に使用する CodeExecutor（指定しない場合はインスタンス既定値）。

        Returns:
            EvalRunResult: テストの実行結果。
        """
        eval_cases = []
        if isinstance(test_cases_data, dict):
            raw_cases = test_cases_data.get("eval_cases") or test_cases_data.get("cases") or []
            eval_cases = [c if isinstance(c, EvalCase) else EvalCase.model_validate(c) for c in raw_cases]
        elif isinstance(test_cases_data, EvalCaseSet):
            eval_cases = test_cases_data.eval_cases
        else:
            raise TypeError("test_cases_data must be a dict or EvalCaseSet")

        active_cases = [c for c in eval_cases if not getattr(c, "is_negative", False)]
        if not active_cases:
            active_cases = eval_cases

        passed = 0
        failed = 0
        total = len(active_cases) * max(1, pass_k)
        failed_cases: list[FailedCaseDetail] = []
        active_executor = code_executor or self.code_executor

        for k_idx in range(max(1, pass_k)):
            if pass_k > 1:
                print(f"\n[TestRunner] --- pass^k iteration {k_idx + 1}/{pass_k} ---")
            for case in active_cases:
                case_id = f"{case.eval_case_id}_run{k_idx+1}" if pass_k > 1 else case.eval_case_id
                cli_args = list(case.cli_args or [])
                script_rel = case.script_name

                # 1. Google ADK 2.0 純正 run_skill_script 呼び出しの検出
                run_skill_call = None
                if hasattr(case, "expected_tool_calls") and case.expected_tool_calls:
                    for tc in case.expected_tool_calls:
                        if isinstance(tc, dict):
                            t_name = tc.get("name") or tc.get("tool", "")
                            t_args = tc.get("args") or {}
                        elif hasattr(tc, "name") and hasattr(tc, "args"):
                            t_name = tc.name
                            t_args = tc.args or {}
                        else:
                            t_name = str(tc)
                            t_args = {}

                        if t_name == "run_skill_script" and isinstance(t_args, dict):
                            run_skill_call = t_args
                            break

                script_args = None
                short_options = None
                positional_args = None

                # 2. 実行対象スクリプトおよび引数の解決
                if run_skill_call is not None:
                    script_rel = run_skill_call.get("file_path") or script_rel
                    script_args = run_skill_call.get("args")
                    short_options = run_skill_call.get("short_options")
                    positional_args = run_skill_call.get("positional_args")

                if not script_rel:
                    script_rel = skill.list_scripts()[0] if skill.list_scripts() else None

                if not script_rel and not hasattr(case, "command"):
                    err_msg = f"No script found in skill '{skill.name}' to execute CLI test."
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            script_name=script_rel or "None",
                            cli_args=cli_args,
                            expected=f"Exit code {case.expected_exit_code}",
                            actual=err_msg,
                            error_type="FileNotFoundError",
                            error_message=err_msg
                        )
                    )
                    continue

                print(f"\n[TestRunner] Running CLI test '{case_id}' on {script_rel}")

                try:
                    # 3. 実行（メタツール CLI か スキルスクリプトかで適切に分岐）
                    if script_rel in ("edd", "cli") or getattr(case, "command", None) in ("edd", "cli"):
                        exec_cmd = [sys.executable, "-m", "edd_agent_tools.cli", *cli_args]
                        proc = subprocess.run(
                            exec_cmd,
                            capture_output=True,
                            text=True,
                            cwd=skill.root_dir,
                            timeout=timeout_seconds
                        )
                        stdout = proc.stdout or ""
                        stderr = proc.stderr or ""
                        exit_code = proc.returncode
                    else:
                        # スキルスクリプト: Google ADK 2.0 公式 SkillToolset (run_skill_script) / BaseCodeExecutor に一本化
                        if script_args is None and short_options is None and positional_args is None:
                            script_args = cli_args

                        res = skill.execute_script(
                            script_name=script_rel,
                            args=script_args,
                            short_options=short_options,
                            positional_args=positional_args,
                            code_executor=active_executor,
                            timeout=timeout_seconds
                        )
                        stdout = res.get("stdout", "")
                        stderr = res.get("stderr", "")
                        exit_code = res.get("exit_code", 0 if res.get("status") == "success" else 1)

                    # 4. アサーション検証
                    cli_failed = False
                    fail_reasons = []

                    # Exit Code 検証
                    if exit_code != case.expected_exit_code:
                        cli_failed = True
                        fail_reasons.append(
                            f"Expected exit code {case.expected_exit_code}, got {exit_code}. Stderr: {stderr.strip()}"
                        )

                    # Stdout キーワード検証
                    if case.expected_stdout_contains:
                        for expected_kw in case.expected_stdout_contains:
                            if expected_kw not in stdout:
                                cli_failed = True
                                fail_reasons.append(
                                    f"Expected stdout to contain '{expected_kw}', but was missing. Stdout: {stdout.strip()}"
                                )

                    if cli_failed:
                        failed += 1
                        failed_cases.append(
                            FailedCaseDetail(
                                eval_case_id=case_id,
                                script_name=script_rel,
                                cli_args=cli_args,
                                expected=f"Exit code {case.expected_exit_code}, stdout: {case.expected_stdout_contains}",
                                actual=f"Exit code {exit_code}, stdout: {stdout.strip()[:200]}",
                                error_type="CliAssertionError",
                                error_message="; ".join(fail_reasons)
                            )
                        )
                        print(f"[TestRunner] ❌ Case '{case_id}' failed: {'; '.join(fail_reasons)}")
                    else:
                        print(f"[TestRunner] ✅ Case '{case_id}' passed (Exit code: {exit_code})")
                        passed += 1

                except subprocess.TimeoutExpired:
                    failed += 1
                    err_msg = f"Script execution timed out after {timeout_seconds} seconds."
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            script_name=script_rel,
                            cli_args=cli_args,
                            expected=f"Execution completes within {timeout_seconds}s",
                            actual=err_msg,
                            error_type="TimeoutError",
                            error_message=err_msg
                        )
                    )
                    print(f"[TestRunner] ❌ Case '{case_id}' timeout")
                except Exception as e:
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            script_name=script_rel,
                            cli_args=cli_args,
                            expected=f"Exit code {case.expected_exit_code}",
                            actual=str(e),
                            error_type=type(e).__name__,
                            error_message=str(e)
                        )
                    )
                    print(f"[TestRunner] ❌ Case '{case_id}' error: {e}")


        accuracy = passed / total if total > 0 else 0.0

        detail_report = EvalDetailReport(
            skill_name=skill.name,
            test_type="contract",
            timestamp=datetime.now(timezone.utc).isoformat(),
            total=total,
            passed=passed,
            failed=failed,
            accuracy=accuracy,
            failed_cases=failed_cases
        )

        results_dir = Path(skill.root_dir) / "tests" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        report_path = results_dir / "latest_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(detail_report.model_dump(), f, ensure_ascii=False, indent=2)

        return EvalRunResult(
            passed=passed,
            failed=failed,
            total=total,
            accuracy=accuracy,
            detail_file_path=str(report_path)
        )
