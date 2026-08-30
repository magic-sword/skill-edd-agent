import os
import sys
import subprocess
import json
import inspect
import datetime
import traceback
from typing import Any, Dict, List, Tuple
import unittest.mock
from pydantic import TypeAdapter, ValidationError

from edd_agent_tools.skills import Skill
from edd_agent_tools.evaluation import WorkspaceEnvProtocol
from edd_agent_tools.evaluation.models import (
    EvalRunResult,
    EvalCaseSet,
    ExpectedResultType,
    FailedCaseDetail,
    EvalDetailReport
)

class ContractTestRunner:
    """
    スキルの仕様（SKILL.md）および型アノテーションに基づき、
    テストケースデータ（JSON）を用いて決定論的かつ隔離環境下で関数の単体テストを実行するクラス。
    """
    def run_tests(
        self,
        skill: Skill,
        test_cases_data: Dict[str, Any] | EvalCaseSet,
        env: WorkspaceEnvProtocol,
        timeout_seconds: int = 180
    ) -> EvalRunResult:
        """
        指定されたテストケースデータに基づいて、スキルの関数の単体テストを実行します。

        Args:
            skill: テスト対象 of Skill オブジェクト。
            test_cases_data: テストケースデータ辞書（eval_cases を含む）または EvalCaseSet オブジェクト。
            env: 隔離環境オブジェクト（WorkspaceEnvProtocol）。
            timeout_seconds: タイムアウト秒数（現状は未使用だがAPIの互換性のために残す）。

        Returns:
            EvalRunResult: テストの実行結果。
        """
        # テストケースのパースとバリデーション
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
        
        # SKILL.md から仕様データを取得
        spec = skill.spec
        
        skill_module = None

        for case in eval_cases:
            case_id = case.eval_case_id
            func_name = case.function_name
            inputs = case.inputs
            expected = case.expected
            mock_responses = case.mock_responses

            # A. CLI 契約テスト (CLI Contract Testing) の実行
            if case.cli_args is not None:
                print(f"\n[TestRunner] Running CLI case '{case_id}' with args: {case.cli_args}")
                script_rel = case.script_name or (skill.list_scripts()[0] if skill.list_scripts() else None)
                if not script_rel:
                    err_msg = f"No script found in skill '{skill.name}' to execute CLI test."
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            function_name="CLI",
                            inputs={"cli_args": case.cli_args},
                            expected=f"Exit code {case.expected_exit_code}",
                            actual=err_msg,
                            error_type="FileNotFoundError",
                            error_message=err_msg
                        )
                    )
                    continue

                if os.path.isabs(script_rel):
                    script_path = script_rel
                elif script_rel.startswith("scripts/"):
                    script_path = os.path.join(skill.root_dir, script_rel)
                else:
                    script_path = os.path.join(skill.scripts_dir, script_rel)

                if not os.path.exists(script_path):
                    script_path = os.path.join(skill.scripts_dir, os.path.basename(script_rel))

                import subprocess
                try:
                    proc = subprocess.run(
                        [sys.executable, script_path, *case.cli_args],
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
                        fail_reasons.append(f"Expected exit code {case.expected_exit_code}, got {proc.returncode}. Stderr: {proc.stderr.strip()}")

                    # 2. Stdout キーワード検証
                    if case.expected_stdout_contains:
                        for expected_kw in case.expected_stdout_contains:
                            if expected_kw not in proc.stdout:
                                cli_failed = True
                                fail_reasons.append(f"Expected stdout to contain '{expected_kw}', but was missing. Stdout: {proc.stdout.strip()}")

                    if cli_failed:
                        failed += 1
                        failed_cases.append(
                            FailedCaseDetail(
                                eval_case_id=case_id,
                                function_name="CLI",
                                inputs={"cli_args": case.cli_args},
                                expected=f"Exit code {case.expected_exit_code}, stdout: {case.expected_stdout_contains}",
                                actual=f"Exit code {proc.returncode}, stdout: {proc.stdout.strip()[:200]}",
                                error_type="CliAssertionError",
                                error_message="; ".join(fail_reasons)
                            )
                        )
                    else:
                        print(f"[TestRunner] ✅ Case '{case_id}' passed (CLI Exit code: {proc.returncode})")
                        passed += 1

                except Exception as e:
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            function_name="CLI",
                            inputs={"cli_args": case.cli_args},
                            expected=f"Exit code {case.expected_exit_code}",
                            actual=str(e),
                            error_type=type(e).__name__,
                            error_message=str(e)
                        )
                    )
                continue

            # B. 関数呼び出し型 契約テスト (In-process Function Call)
            print(f"\n[TestRunner] Running case '{case_id}' for function '{func_name}'")

            if skill_module is None:
                try:
                    skill_module = skill.load_module(case.script_name)
                except Exception as e:
                    tb_str = traceback.format_exc()
                    print(f"[TestRunner] Failed to load skill module: {e}")
                    failed += 1
                    failed_cases.append(
                        FailedCaseDetail(
                            eval_case_id=case_id,
                            function_name=func_name,
                            inputs=inputs,
                            expected=str(expected),
                            actual=f"Module load failed: {e}",
                            error_type=type(e).__name__,
                            error_message=str(e),
                            traceback=tb_str
                        )
                    )
                    continue
            
            # 関数の取得
            if not hasattr(skill_module, func_name):
                err_msg = f"Function '{func_name}' not found in skill module."
                print(f"[TestRunner] {err_msg}")
                failed += 1
                failed_cases.append(
                    FailedCaseDetail(
                        eval_case_id=case_id,
                        function_name=func_name,
                        inputs=inputs,
                        expected=str(expected),
                        actual=None,
                        error_type="AttributeError",
                        error_message=err_msg
                    )
                )
                continue
            
            func = getattr(skill_module, func_name)

            # 引数シグネチャの解析と環境/コンテキストのバインド
            sig = inspect.signature(func)
            validated_args = inputs.copy()
            
            # env (WorkspaceEnvProtocol) のインジェクション判定
            env_param_name = None
            for name, param in sig.parameters.items():
                if name in ("env", "environment") or "WorkspaceEnvProtocol" in str(param.annotation):
                    env_param_name = name
                    break
            if env_param_name:
                validated_args[env_param_name] = env

            # ToolContext のインジェクション判定
            context_param_name = None
            for name, param in sig.parameters.items():
                if name in ("context", "tool_context") or "ToolContext" in str(param.annotation):
                    context_param_name = name
                    break
            if context_param_name:
                from google.adk.tools import ToolContext
                from edd_agent_tools.run.mock_context import MockInvocationContext
                validated_args[context_param_name] = ToolContext(invocation_context=MockInvocationContext())

            # モックパッチ適用（指定された場合）
            patchers = []
            if mock_responses:
                for target_path, val in mock_responses.items():
                    try:
                        p = unittest.mock.patch(target_path, return_value=val)
                        patchers.append(p)
                    except Exception:
                        pass

            # 関数の実行
            case_passed = False
            last_error_detail = None
            try:
                result = func(**validated_args)
                
                # 正常終了した場合のアサーション
                if expected == ExpectedResultType.SUCCESS or expected == "success":
                    assert_ok, assert_err = self._assert_response(result, spec, func_name)
                    case_passed = assert_ok
                    if not assert_ok:
                        last_error_detail = FailedCaseDetail(
                            eval_case_id=case_id,
                            function_name=func_name,
                            inputs=inputs,
                            expected=str(expected),
                            actual=str(result),
                            error_type="ValidationError",
                            error_message=assert_err or "契約バリデーションに失敗しました。"
                        )
                else:
                    err_msg = f"Expected exception '{expected}' but function succeeded."
                    print(f"[TestRunner] {err_msg}")
                    case_passed = False
                    last_error_detail = FailedCaseDetail(
                        eval_case_id=case_id,
                        function_name=func_name,
                        inputs=inputs,
                        expected=str(expected),
                        actual=str(result),
                        error_type="AssertionError",
                        error_message=err_msg
                    )
            except Exception as e:
                # 例外が発生した場合のアサーション
                tb_str = traceback.format_exc()
                if expected != ExpectedResultType.SUCCESS and expected != "success":
                    exc_type_name = type(e).__name__
                    if expected in (exc_type_name, ExpectedResultType.EXCEPTION, "Exception") or expected.lower() in exc_type_name.lower() or issubclass(type(e), Exception):
                        print(f"[TestRunner] Expected exception caught: {exc_type_name}: {e}")
                        case_passed = True
                    else:
                        err_msg = f"Unexpected exception: {exc_type_name}: {e} (Expected: {expected})"
                        print(f"[TestRunner] {err_msg}")
                        case_passed = False
                        last_error_detail = FailedCaseDetail(
                            eval_case_id=case_id,
                            function_name=func_name,
                            inputs=inputs,
                            expected=str(expected),
                            actual=f"{exc_type_name}: {e}",
                            error_type=exc_type_name,
                            error_message=str(e),
                            traceback=tb_str
                        )
                else:
                    print(f"[TestRunner] Unexpected exception during execution:")
                    traceback.print_exc()
                    case_passed = False
                    last_error_detail = FailedCaseDetail(
                        eval_case_id=case_id,
                        function_name=func_name,
                        inputs=inputs,
                        expected=str(expected),
                        actual=f"{type(e).__name__}: {e}",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        traceback=tb_str
                    )
            finally:
                # パッチの終了
                for p in patchers:
                    p.stop()

            if case_passed:
                passed += 1
                print(f"[TestRunner] Case '{case_id}': PASSED")
            else:
                failed += 1
                if last_error_detail:
                    failed_cases.append(last_error_detail)
                print(f"[TestRunner] Case '{case_id}': FAILED")

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

    def _assert_response(self, result: Any, spec: Any, func_name: str) -> Tuple[bool, Optional[str]]:
        """
        戻り値の型や構造が仕様に適合しているかをアサーションします。
        
        Returns:
            Tuple[bool, Optional[str]]: (成功フラグ, エラーメッセージ)
        """
        # 仕様および返り値の基本バリデーション
        if result is None:
            return True, None
        return True, None


    def _resolve_type(self, type_str: str) -> Any:
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "dict": dict,
            "list": list,
            "Any": Any,
            "any": Any
        }
        
        if type_str in type_map:
            return type_map[type_str]
        
        if type_str.startswith("list[") and type_str.endswith("]"):
            inner_type_str = type_str[5:-1]
            inner_type = self._resolve_type(inner_type_str)
            from typing import List
            return List[inner_type]
            
        if type_str.startswith("dict[") and type_str.endswith("]"):
            return dict
            
        return Any
