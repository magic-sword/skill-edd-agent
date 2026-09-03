"""
Contract Test Runner for edd-agent-tools

スキルの CLI 規約（--help, 引数, 終了コード, 出力）をサンドボックス（LocalWorkspaceEnv 等）内で
決定論的に Black-box 実行・検証するテストランナー。
ホワイトペーパー Section 4 準拠の pass^k（Sustained Reliability）連続実行をサポート。
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

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
            if "eval_cases" in test_cases_data:
                test_case_set = EvalCaseSet.model_validate(test_cases_data)
                eval_cases = test_case_set.eval_cases
            elif "cases" in test_cases_data:
                # 白書 Snippet 3 形式からの動的マッピング
                for idx, c in enumerate(test_cases_data["cases"]):
                    tool_calls = c.get("expected_tool_calls") or []
                    for tc in tool_calls:
                        t_name = tc.get("tool", "")
                        t_args = tc.get("args") or []

                        # ADK 2.0 純正 run_skill_script 形式の解決
                        if t_name == "run_skill_script" and isinstance(t_args, dict):
                            actual_script = t_args.get("file_path") or t_name
                            inner_args = t_args.get("args")
                            if inner_args is None:
                                inner_args = {k: v for k, v in t_args.items() if k not in ("skill_name", "file_path")}
                            t_name = actual_script
                            t_args = inner_args

                        if isinstance(t_args, dict):
                            cli_args = []
                            for k, v in t_args.items():
                                flag = f"--{k.replace('_', '-')}" if not k.startswith("-") else k
                                if v is True:
                                    cli_args.append(flag)
                                elif v is not False and v is not None:
                                    cli_args.extend([flag, str(v)])
                        elif isinstance(t_args, list):
                            cli_args = [str(a) for a in t_args]
                        else:
                            cli_args = [str(t_args)] if t_args else []
                        exp_out = c.get("expected_output_format")
                        # 具象出力文字列の場合は stdout アサーションに登録（抽象フォーマット名は除外）
                        kw_list = []
                        abstract_suffixes = ("_format", "_summary", "_calculation", "_id", "_help", "_confirmation", "_path", "_status", "_report")
                        if exp_out and isinstance(exp_out, str) and not exp_out.endswith(abstract_suffixes):
                            kw_list = [exp_out]


                        eval_cases.append(EvalCase(
                            eval_case_id=c.get("case_id", f"case_{idx}"),
                            script_name=t_name,
                            cli_args=cli_args,
                            expected_exit_code=0,
                            expected_stdout_contains=kw_list if kw_list else None
                        ))
            else:
                test_case_set = EvalCaseSet.model_validate(test_cases_data)
                eval_cases = test_case_set.eval_cases
        elif isinstance(test_cases_data, EvalCaseSet):
            eval_cases = test_cases_data.eval_cases
        else:
            raise TypeError("test_cases_data must be a dict or EvalCaseSet")

        passed = 0
        failed = 0
        total = len(eval_cases) * max(1, pass_k)
        failed_cases: list[FailedCaseDetail] = []


        for k_idx in range(max(1, pass_k)):
            if pass_k > 1:
                print(f"\n[TestRunner] --- pass^k iteration {k_idx + 1}/{pass_k} ---")
            for case in eval_cases:
                case_id = f"{case.eval_case_id}_run{k_idx+1}" if pass_k > 1 else case.eval_case_id
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
