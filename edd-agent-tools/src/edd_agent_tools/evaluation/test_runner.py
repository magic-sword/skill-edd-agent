import os
import sys
import subprocess
import json
import datetime
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from edd_agent_tools.core.entity import Skill
from edd_agent_tools.core.protocols import WorkspaceEnvProtocol
from edd_agent_tools.models import (
    EvalRunResult,
    EvalCaseSet,
    FailedCaseDetail,
    EvalDetailReport
)


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
        timeout_seconds: int = 180
    ) -> EvalRunResult:
        """
        指定されたテストケースデータに基づいて、スキルの CLI 契約テストを実行します。

        Args:
            skill: テスト対象の Skill オブジェクト。
            test_cases_data: テストケースデータ辞書（eval_cases を含む）または EvalCaseSet オブジェクト。
            env: 隔離環境オブジェクト（WorkspaceEnvProtocol）。
            timeout_seconds: タイムアウト秒数。

        Returns:
            EvalRunResult: テストの実行結果。
        """
        if isinstance(test_cases_data, dict):
            test_case_set = EvalCaseSet.model_validate(test_cases_data)
        elif isinstance(test_cases_data, EvalCaseSet):
            test_case_set = test_cases_data
        else:
            raise TypeError("test_cases_data must be a dict or EvalCaseSet")

        eval_cases = test_case_set.eval_cases
        passed = 0
        failed = 0
        total = len(eval_cases)
        failed_cases: list[FailedCaseDetail] = []

        for case in eval_cases:
            case_id = case.eval_case_id
            cli_args = case.cli_args or []

            print(f"\n[TestRunner] Running CLI case '{case_id}' with args: {cli_args}")
            script_rel = case.script_name or (skill.list_scripts()[0] if skill.list_scripts() else None)

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

            # コマンドの構築
            if script_rel in ("edd", "cli") or getattr(case, "command", None) in ("edd", "cli"):
                cmd = [sys.executable, "-m", "edd_agent_tools.cli", *cli_args]
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

            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=skill.root_dir,
                    timeout=timeout_seconds
                )

                cli_failed = False
                fail_reasons = []

                # 1. Exit Code 検証
                if proc.returncode != case.expected_exit_code:
                    cli_failed = True
                    fail_reasons.append(
                        f"Expected exit code {case.expected_exit_code}, got {proc.returncode}. Stderr: {proc.stderr.strip()}"
                    )

                # 2. Stdout キーワード検証
                if case.expected_stdout_contains:
                    for expected_kw in case.expected_stdout_contains:
                        if expected_kw not in proc.stdout:
                            cli_failed = True
                            fail_reasons.append(
                                f"Expected stdout to contain '{expected_kw}', but was missing. Stdout: {proc.stdout.strip()}"
                            )

                if cli_failed:
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            script_name=script_rel,
                            cli_args=cli_args,
                            expected=f"Exit code {case.expected_exit_code}, stdout: {case.expected_stdout_contains}",
                            actual=f"Exit code {proc.returncode}, stdout: {proc.stdout.strip()[:200]}",
                            error_type="CliAssertionError",
                            error_message="; ".join(fail_reasons)
                        )
                    )
                    print(f"[TestRunner] ❌ Case '{case_id}' failed: {'; '.join(fail_reasons)}")
                else:
                    print(f"[TestRunner] ✅ Case '{case_id}' passed (CLI Exit code: {proc.returncode})")
                    passed += 1

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
        summary_detail = f"全 {total} 件中 {passed} 件成功 (精度: {accuracy:.2%})"

        # 詳細レポートの作成と保存
        report = EvalDetailReport(
            skill_name=skill.name,
            test_type="contract",
            timestamp=datetime.datetime.now().isoformat() + "Z",
            passed=passed,
            failed=failed,
            total=total,
            accuracy=accuracy,
            details=summary_detail,
            failed_cases=failed_cases
        )
        detail_path = skill.tests.save_report(report, test_type="contract")

        return EvalRunResult(
            passed=passed,
            failed=failed,
            total=total,
            accuracy=accuracy,
            detail_file_path=detail_path
        )
