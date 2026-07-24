import os
import json
import inspect
from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.evaluation.models import EvalRunResult, TrajectoryEvalSet

class TrajectoryTestExecutor:
    """TrajectoryEvalSet を読み込み、決定論的なツール軌跡（Tool Trajectory）アサーションを実行するクラス。"""
    def __init__(self):
        self._skills_state = SkillsState()

    def run_tests(self, skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
        """指定されたスキルと TrajectoryEvalSet ファイルに基づき、決定論的なツール軌跡テストを実行します。

        Args:
            skill_name: テスト対象のスキル名。
            eval_set_path: TrajectoryEvalSet JSON ファイルへの絶対パス。
            env: サンドボックス環境（WorkspaceEnvProtocol）。

        Returns:
            EvalRunResult オブジェクト。
        """
        try:
            if not os.path.exists(eval_set_path):
                print(f"[TrajectoryTestExecutor] Error: Eval set file not found: {eval_set_path}")
                return EvalRunResult(passed=0, failed=1, total=1, accuracy=0.0)

            with open(eval_set_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            eval_set = TrajectoryEvalSet.model_validate(data)

            # 対象スキルのロード
            target_skill = self._skills_state.get_skill(skill_name)
            skill_module = target_skill.load_module()
            design_json = target_skill.load_design()

            passed = 0
            failed = 0
            total = len(eval_set.eval_cases)
            details = []

            for case in eval_set.eval_cases:
                eval_id = case.eval_id
                print(f"\n[TrajectoryTestExecutor] Evaluating case '{eval_id}' for skill '{skill_name}'")

                case_passed = True
                failure_reasons = []

                for turn in case.conversation:
                    expected_tool_uses = turn.intermediate_data.tool_uses
                    user_inputs = turn.user_content

                    # ユーザー入力からの引数復元
                    actual_tool_calls = []

                    # design.jsonから主要関数名を取得
                    func_names = []
                    if design_json and "functions" in design_json:
                        func_names = [f["name"] for f in design_json["functions"]]
                    if not func_names:
                        func_names = [
                            attr for attr in dir(skill_module) 
                            if not attr.startswith("_") and inspect.isfunction(getattr(skill_module, attr))
                        ]

                    for func_name in func_names:
                        if hasattr(skill_module, func_name):
                            func = getattr(skill_module, func_name)
                            if not callable(func):
                                continue

                            sig = inspect.signature(func)
                            
                            # 引数の準備
                            call_kwargs = {}
                            for param_name in sig.parameters:
                                if param_name == "env":
                                    call_kwargs["env"] = env
                                elif param_name in user_inputs:
                                    call_kwargs[param_name] = user_inputs[param_name]
                                elif "skill_name" in param_name and "skill_name" in user_inputs:
                                    call_kwargs[param_name] = user_inputs["skill_name"]
                                elif "output_path" in param_name and "output_path" in user_inputs:
                                    call_kwargs[param_name] = user_inputs["output_path"]
                                elif "eval_set_path" in param_name and "eval_set_path" in user_inputs:
                                    call_kwargs[param_name] = user_inputs["eval_set_path"]

                            try:
                                # 試行と呼び出しトレースの記録
                                func(**call_kwargs)
                                actual_tool_calls.append({
                                    "name": func_name,
                                    "args": {k: v for k, v in call_kwargs.items() if k != "env"}
                                })
                            except Exception as ex:
                                failure_reasons.append(f"Function {func_name} execution error: {ex}")

                    # 決定論的アサーション (IN_ORDER 比較)
                    actual_idx = 0
                    for expected_tool in expected_tool_uses:
                        exp_name = expected_tool.name
                        exp_args = expected_tool.args

                        found = False
                        while actual_idx < len(actual_tool_calls):
                            actual_call = actual_tool_calls[actual_idx]
                            actual_idx += 1

                            if actual_call["name"] == exp_name or exp_name in actual_call["name"] or actual_call["name"] in exp_name:
                                args_match = True
                                for k, expected_v in exp_args.items():
                                    if k in actual_call["args"]:
                                        act_v = str(actual_call["args"][k])
                                        exp_v = str(expected_v)
                                        if act_v != exp_v and exp_v not in act_v:
                                            args_match = False
                                            break

                                if args_match:
                                    found = True
                                    break

                        if not found:
                            case_passed = False
                            failure_reasons.append(f"Expected tool '{exp_name}' with args {exp_args} not found in actual trajectory.")

                if case_passed and len(failure_reasons) == 0:
                    passed += 1
                    status = "passed"
                    print(f" -> Case '{eval_id}' PASSED")
                else:
                    failed += 1
                    status = "failed"
                    print(f" -> Case '{eval_id}' FAILED: {failure_reasons}")

                details.append({
                    "eval_id": eval_id,
                    "status": status,
                    "reasons": failure_reasons
                })

            accuracy = (passed / total) if total > 0 else 0.0

            detail_file_path = os.path.join(
                os.path.dirname(eval_set_path),
                f"{skill_name}_trajectory_details.json"
            )
            with open(detail_file_path, "w", encoding="utf-8") as f:
                json.dump(details, f, indent=2, ensure_ascii=False)

            return EvalRunResult(
                passed=passed,
                failed=failed,
                total=total,
                accuracy=accuracy,
                detail_file_path=detail_file_path
            )

        except Exception as e:
            print(f"[TrajectoryTestExecutor] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return EvalRunResult(passed=0, failed=1, total=1, accuracy=0.0)
