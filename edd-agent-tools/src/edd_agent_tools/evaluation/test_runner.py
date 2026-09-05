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
    """

    def run_tests(
        self,
        skill: Skill,
        test_cases_data: Dict[str, Any] | EvalCaseSet,
        env: WorkspaceEnvProtocol,
        timeout_seconds: int = 180,
        pass_k: int = 1
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

                # 2. 実行対象スクリプトおよび CLI 引数リストの正規化
                if run_skill_call is not None:
                    script_rel = run_skill_call.get("file_path") or script_rel
                    script_args = run_skill_call.get("args")
                    short_options = run_skill_call.get("short_options")
                    positional_args = run_skill_call.get("positional_args")

                    cli_args = []
                    if positional_args and isinstance(positional_args, list):
                        cli_args.extend(str(p) for p in positional_args)
                    if short_options and isinstance(short_options, dict):
                        for sk, sv in short_options.items():
                            s_flag = f"-{sk}" if not sk.startswith("-") else sk
                            if sv is True:
                                cli_args.append(s_flag)
                            elif sv is not False and sv is not None:
                                cli_args.extend([s_flag, str(sv)])
                    if isinstance(script_args, dict):
                        for ak, av in script_args.items():
                            flag = f"--{ak.replace('_', '-')}" if not ak.startswith("-") else ak
                            if av is True:
                                cli_args.append(flag)
                            elif av is not False and av is not None:
                                cli_args.extend([flag, str(av)])
                    elif isinstance(script_args, list):
                        cli_args.extend(str(a) for a in script_args)

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

                # 3. 実行コマンドの構築
                if script_rel in ("edd", "cli") or getattr(case, "command", None) in ("edd", "cli"):
                    cmd = [sys.executable, "-m", "edd_agent_tools.cli", *cli_args]
                    work_dir = skill.root_dir
                else:
                    if os.path.isabs(script_rel):
                        script_path = script_rel
                    elif script_rel.startswith("scripts/"):
                        script_path = os.path.join(skill.root_dir, script_rel)
                    else:
                        script_path = os.path.join(skill.scripts_dir, script_rel)

                    if not os.path.exists(script_path):
                        script_path = os.path.join(skill.scripts_dir, os.path.basename(script_rel))

                    if not os.path.exists(script_path):
                        err_msg = f"Script '{script_rel}' not found in skill '{skill.name}'."
                        failed += 1
                        failed_cases.append(
                            FailedCaseDetail(
                                eval_case_id=case_id,
                                script_name=script_rel,
                                cli_args=cli_args,
                                expected=f"Exit code {case.expected_exit_code}",
                                actual=err_msg,
                                error_type="FileNotFoundError",
                                error_message=err_msg
                            )
                        )
                        continue

                    cmd = [sys.executable, script_path, *cli_args]
                    work_dir = skill.root_dir

                # 4. 決定論的 CLI 実行 (環境変数とタイムアウトを安全に制御)
                print(f"\n[TestRunner] Running CLI test '{case_id}' on {script_rel} with args: {cli_args}")
                env_vars = os.environ.copy()
                env_vars["EDD_SKILL_NAME"] = skill.name
                env_vars["EDD_SKILL_ROOT"] = str(skill.root_dir)

                try:
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        cwd=work_dir,
                        env=env_vars,
                        timeout=timeout_seconds
                    )

                    stdout = proc.stdout or ""
                    stderr = proc.stderr or ""
                    exit_code = proc.returncode

                    cli_failed = False
                    fail_reasons = []

                    # 1. Exit Code 検証
                    if exit_code != case.expected_exit_code:
                        cli_failed = True
                        fail_reasons.append(
                            f"Expected exit code {case.expected_exit_code}, got {exit_code}. Stderr: {stderr.strip()}"
                        )

                    # 2. Stdout キーワード検証
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
                        print(f"[TestRunner] ✅ Case '{case_id}' passed (CLI Exit code: {exit_code})")
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
