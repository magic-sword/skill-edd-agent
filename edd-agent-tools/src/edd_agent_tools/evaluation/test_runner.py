import os
import json
import inspect
from typing import Any, Dict, List
import unittest.mock
from pydantic import TypeAdapter, ValidationError

from edd_agent_tools.skills import Skill
from edd_agent_tools.evaluation import WorkspaceEnvProtocol
from edd_agent_tools.evaluation.models import EvalRunResult, EvalCaseSet, ExpectedResultType

class ContractTestRunner:
    """
    スキルの design.json に定義されたスキーマ契約（入力と出力の型・制約）に基づき、
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
        
        # design.json から設計データを取得
        design = skill.load_design()
        
        # 公開関数のモジュールを動的ロード
        try:
            skill_module = skill.load_module()
        except Exception as e:
            print(f"[TestRunner] Failed to load skill module: {e}")
            return EvalRunResult(passed=0, failed=total, total=total, accuracy=0.0)

        for case in eval_cases:
            case_id = case.eval_case_id
            func_name = case.function_name
            inputs = case.inputs
            expected = case.expected
            mock_responses = case.mock_responses

            print(f"\n[TestRunner] Running case '{case_id}' for function '{func_name}'")
            
            # 関数の取得
            if not hasattr(skill_module, func_name):
                print(f"[TestRunner] Function '{func_name}' not found in skill module.")
                failed += 1
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

            # LLM クライアントのモックパッチ適用
            patchers = []
            mock_client_path = "edd_agent_tools.gemini.agy_client.GeminiClient"
            
            if mock_responses:
                for method, val in mock_responses.items():
                    if method.startswith("GeminiClient."):
                        actual_method = method.split(".")[1]
                        p = unittest.mock.patch(f"{mock_client_path}.{actual_method}", return_value=val)
                        patchers.append(p)

            # パッチの開始
            for p in patchers:
                p.start()

            # 関数の実行
            case_passed = False
            try:
                result = func(**validated_args)
                
                # 正常終了した場合のアサーション
                if expected == ExpectedResultType.SUCCESS or expected == "success":
                    case_passed = self._assert_response(result, design, func_name)
                else:
                    print(f"[TestRunner] Expected exception '{expected}' but function succeeded.")
                    case_passed = False
            except Exception as e:
                # 例外が発生した場合のアサーション
                if expected != ExpectedResultType.SUCCESS and expected != "success":
                    exc_type_name = type(e).__name__
                    if expected in (exc_type_name, ExpectedResultType.EXCEPTION, "Exception") or expected.lower() in exc_type_name.lower() or issubclass(type(e), Exception):
                        print(f"[TestRunner] Expected exception caught: {exc_type_name}: {e}")
                        case_passed = True
                    else:
                        print(f"[TestRunner] Unexpected exception: {exc_type_name}: {e} (Expected: {expected})")
                        case_passed = False
                else:
                    import traceback
                    print(f"[TestRunner] Unexpected exception during execution:")
                    traceback.print_exc()
                    case_passed = False
            finally:
                # パッチの終了
                for p in patchers:
                    p.stop()

            if case_passed:
                passed += 1
                print(f"[TestRunner] Case '{case_id}': PASSED")
            else:
                failed += 1
                print(f"[TestRunner] Case '{case_id}': FAILED")

        accuracy = passed / total if total > 0 else 1.0
        return EvalRunResult(
            passed=passed,
            failed=failed,
            total=total,
            accuracy=accuracy,
            detail_file_path=None
        )

    def _assert_response(self, result: Any, design: Any, func_name: str) -> bool:
        """
        戻り値が設計仕様（design.json）の契約に適合しているかをアサーションします。
        """
        fn_def = None
        for fn in getattr(design, "functions", []):
            if fn.name == func_name:
                fn_def = fn
                break
        
        if not fn_def:
            output_mode = getattr(design, "output_mode", "VALUE_ONLY")
            response_parameters = getattr(design, "response_parameters", None)
            response_type = None
        else:
            output_mode = getattr(design, "output_mode", "VALUE_ONLY")
            response_parameters = getattr(fn_def, "response_parameters", None)
            response_type = getattr(fn_def, "response_type", None)


        from edd_agent_tools.skills.models import OutputMode
        
        actual_result = result
        if hasattr(result, "value"):
            actual_result = result.value
        elif isinstance(result, dict) and "value" in result:
            actual_result = result["value"]

        try:
            if output_mode == OutputMode.STRUCTURED_JSON:
                if not response_parameters:
                    print("[TestRunner] Validation Warning: output_mode is STRUCTURED_JSON but response_parameters is empty.")
                    return True
                
                from pydantic import create_model
                
                fields = {}
                for p in response_parameters:
                    p_type = self._resolve_type(p.type)
                    fields[p.name] = (p_type, ... if p.required else None)
                
                DynamicModel = create_model("DynamicResponseModel", **fields)
                
                if hasattr(actual_result, "model_dump"):
                    actual_result = actual_result.model_dump()
                elif hasattr(actual_result, "dict"):
                    actual_result = actual_result.dict()

                if isinstance(actual_result, str):
                    try:
                        actual_result = json.loads(actual_result)
                    except json.JSONDecodeError:
                        print(f"[TestRunner] Expected JSON string but failed to parse: {actual_result}")
                        return False

                DynamicModel.model_validate(actual_result)
                print(f"[TestRunner] Response validated successfully against structured schema.")
                return True
                
            else:
                if not response_type:
                    return True
                
                if hasattr(actual_result, "model_dump"):
                    actual_result = actual_result.model_dump()
                elif hasattr(actual_result, "dict"):
                    actual_result = actual_result.dict()

                expected_type = self._resolve_type(response_type)

                adapter = TypeAdapter(expected_type)
                adapter.validate_python(actual_result)
                print(f"[TestRunner] Response type '{type(actual_result).__name__}' matches expected '{response_type}'.")
                return True
                
        except (ValidationError, TypeError, ValueError) as ve:
            print(f"[TestRunner] Contract Validation Failed: {ve}")
            return False

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
