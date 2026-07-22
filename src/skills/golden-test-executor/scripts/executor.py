import os
import json
import inspect
from pydantic import BaseModel, Field
from google.genai import types
from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import GeminiClient
from edd_agent_tools.evaluation.models import EvalRunResult
from .models import JudgeResult

from typing import List, Dict, Any, Optional

class ExpectedToolUse(BaseModel):
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)

class GoldenCase(BaseModel):
    eval_case_id: str
    function_name: str
    inputs: List[InputParameter]
    expected_response_rubric: str
    expected_trajectory: Optional[List[ExpectedToolUse]] = Field(default_factory=list)

class GoldenCaseSet(BaseModel):
    eval_set_id: str
    eval_cases: List[GoldenCase]


class SkillExecutor:
    """ゴールデンデータセットを用いて、サンドボックス環境上で関数を実行し、意味的整合性をLLM Judgeで判定・評価するクラス。"""
    def __init__(self):
        self._skills_state = SkillsState()
        self._gemini_client = GeminiClient()

    def run_tests(self, skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
        """指定されたスキルとゴールデンデータセットを用い、仮想環境上で意味的テストを実行・評価します。

        Args:
            skill_name: テスト対象のスキル名。
            eval_set_path: ゴールデンデータテストケースが記述されたJSONファイルの絶対パス。
            env: テストを実行するサンドボックス環境（WorkspaceEnvProtocol）。

        Returns:
            テスト実行結果オブジェクト (EvalRunResult)。
        """
        try:
            # 1. ゴールデンテストセットのロード
            if not os.path.exists(eval_set_path):
                print(f"Error: Golden eval set file not found at {eval_set_path}")
                return EvalRunResult(passed=0, failed=1, total=1, accuracy=0.0)

            with open(eval_set_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            case_set = GoldenCaseSet.model_validate(data)

            # 2. テスト対象スキルのロード
            target_skill = self._skills_state.get_skill(skill_name)
            skill_module = target_skill.load_module()

            passed = 0
            failed = 0
            total = len(case_set.eval_cases)
            details = []

            # 3. 各ケースの実行とLLM Judgeによる評価
            for case in case_set.eval_cases:
                case_id = case.eval_case_id
                func_name = case.function_name
                inputs_list = case.inputs
                rubric = case.expected_response_rubric

                print(f"\n[GoldenExecutor] Running case '{case_id}' for function '{func_name}'")

                # List[InputParameter] -> Dict[str, Any] への型復元・変換
                inputs = {}
                for param in inputs_list:
                    val_str = param.value
                    if val_str.lower() == "true":
                        val = True
                    elif val_str.lower() == "false":
                        val = False
                    else:
                        try:
                            if "." in val_str:
                                val = float(val_str)
                            else:
                                val = int(val_str)
                        except ValueError:
                            val = val_str
                    inputs[param.name] = val

                # 関数の取得と実行
                if not hasattr(skill_module, func_name):
                    print(f"Error: Function '{func_name}' not found in skill module.")
                    failed += 1
                    continue

                func = getattr(skill_module, func_name)
                sig = inspect.signature(func)
                validated_args = inputs.copy()

                # envのインジェクション
                if "env" in sig.parameters:
                    validated_args["env"] = env

                try:
                    # サンドボックス上での実行
                    res_val = func(**validated_args)

                    # 戻り値を文字列化
                    if isinstance(res_val, BaseModel):
                        output_str = res_val.model_dump_json(indent=2)
                    elif isinstance(res_val, (dict, list)):
                        output_str = json.dumps(res_val, indent=2, ensure_ascii=False)
                    else:
                        output_str = str(res_val)

                except Exception as ex:
                    print(f"Execution failed with error: {ex}")
                    failed += 1
                    details.append({
                        "case_id": case_id,
                        "status": "failed",
                        "score": 0,
                        "reason": f"関数の実行中に例外が発生しました: {ex}"
                    })
                    continue

                # 期待される経路（expected_trajectory）の埋め込み
                trajectory_rubric = ""
                if case.expected_trajectory and len(case.expected_trajectory) > 0:
                    traj_str = json.dumps([t.model_dump() for t in case.expected_trajectory], indent=2, ensure_ascii=False)
                    trajectory_rubric = f"\n\n【期待される実行経路（ツール呼び出しシーケンス）】\n{traj_str}\n※出力結果だけでなく、上記の期待されるツールの実行順序や引数の目的が適切に満たされているかも評価してください。"

                # LLM-as-Judge 判定プロンプトの構築
                judge_prompt = f"""あなたは公正な判定を行うLLM Judgeです。
テスト対象スキルに以下の引数を入力して実行した結果、得られた出力が、期待される「ルーブリック（合格基準）」および「期待される実行経路」を満たしているかを厳格に判定してください。

【入力引数】
{json.dumps(inputs, indent=2, ensure_ascii=False)}

【実際の出力内容】
{output_str}

【満たすべきルーブリック（合格基準）】
{rubric}{trajectory_rubric}
"""

                # Geminiでの採点（構造化出力）
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=JudgeResult,
                    temperature=0.2
                )
                response = self._gemini_client.request(judge_prompt).execute(config=config)

                raw_text = response.text.strip()
                if raw_text.startswith("```json") and raw_text.endswith("```"):
                    json_str = raw_text[len("```json"):-len("```")].strip()
                else:
                    json_str = raw_text

                judge_res = JudgeResult.model_validate_json(json_str)

                print(f"[LLM-Judge] Score: {judge_res.score}/10, Passed: {judge_res.passed}, Reason: {judge_res.reason}")

                if judge_res.passed:
                    passed += 1
                else:
                    failed += 1

                details.append({
                    "case_id": case_id,
                    "status": "passed" if judge_res.passed else "failed",
                    "score": judge_res.score,
                    "reason": judge_res.reason
                })

            accuracy = (passed / total) if total > 0 else 0.0

            # 詳細結果のファイル保存
            detail_file_path = os.path.join(
                os.path.dirname(eval_set_path),
                f"{skill_name}_golden_details.json"
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
            print(f"Unexpected error in GoldenTestExecutor: {e}")
            import traceback
            traceback.print_exc()
            return EvalRunResult(passed=0, failed=1, total=1, accuracy=0.0)
