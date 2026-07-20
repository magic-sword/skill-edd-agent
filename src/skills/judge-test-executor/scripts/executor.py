import os
import json
import inspect
from pydantic import BaseModel, Field
from google.genai import types
from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.gemini import GeminiClient
from edd_agent_tools.evaluation.models import EvalRunResult
from .models import CaseEvaluation

# テストケース側のデータパース用
from typing import List, Dict, Any

class InputParameter(BaseModel):
    name: str
    value: str

class RubricItem(BaseModel):
    criterion: str
    description: str
    weight: float

class JudgeCase(BaseModel):
    eval_case_id: str
    function_name: str
    inputs: List[InputParameter]
    rubrics: List[RubricItem]

class JudgeCaseSet(BaseModel):
    eval_set_id: str
    eval_cases: List[JudgeCase]


class SkillExecutor:
    """ルーブリック評価セットを用いて、サンドボックス環境上で関数を実行し、多角的な基準でLLM Judgeによる評価を行うクラス。"""
    def __init__(self):
        self._skills_state = SkillsState()
        self._gemini_client = GeminiClient()

    def run_tests(self, skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
        """指定されたスキルとルーブリック評価セットを用い、仮想環境上で多角的テストを実行・評価します。

        Args:
            skill_name: テスト対象のスキル名。
            eval_set_path: ルーブリック評価セットが記述されたJSONファイルの絶対パス。
            env: テストを実行するサンドボックス環境（WorkspaceEnvProtocol）。

        Returns:
            テスト実行結果オブジェクト (EvalRunResult)。
        """
        try:
            # 1. ルーブリック評価セットのロード
            if not os.path.exists(eval_set_path):
                print(f"Error: Rubric eval set file not found at {eval_set_path}")
                return EvalRunResult(passed=0, failed=1, total=1, accuracy=0.0)

            with open(eval_set_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            case_set = JudgeCaseSet.model_validate(data)

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
                rubrics = case.rubrics

                print(f"\n[JudgeExecutor] Running case '{case_id}' for function '{func_name}'")

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
                        "passed": False,
                        "reason": f"関数の実行中に例外が発生しました: {ex}"
                    })
                    continue

                # ルーブリック項目の一覧をテキスト化
                rubrics_text = ""
                for idx, item in enumerate(rubrics):
                    rubrics_text += f"{idx+1}. 基準項目名: {item.criterion}\n   評価詳細: {item.description}\n   配点重み: {item.weight}\n"

                # LLM-as-Judge 判定プロンプトの構築
                judge_prompt = f"""あなたは公正な判定を行うLLM Judgeです。
テスト対象スキルに以下の引数を入力して実行した結果、得られた出力が、期待される「多角的な評価ルーブリック項目」を十分に満たしているかを個別に厳格に判定・採点（各項目0〜10点、合格は8点以上）してください。

【入力引数】
{json.dumps(inputs, indent=2, ensure_ascii=False)}

【実際の出力内容】
{output_str}

【満たすべきルーブリック項目リスト】
{rubrics_text}
"""

                # Geminiでの採点（構造化出力）
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CaseEvaluation,
                    temperature=0.2
                )
                response = self._gemini_client.request(judge_prompt).execute(config=config)

                raw_text = response.text.strip()
                if raw_text.startswith("```json") and raw_text.endswith("```"):
                    json_str = raw_text[len("```json"):-len("```")].strip()
                else:
                    json_str = raw_text

                judge_res = CaseEvaluation.model_validate_json(json_str)

                # 各項目評価のログ出力
                print(f"[LLM-Judge] Case '{case_id}' Overall Passed: {judge_res.passed}")
                for eval_item in judge_res.rubric_evaluations:
                    print(f"  - [{eval_item.criterion}] Score: {eval_item.score}/10, Passed: {eval_item.passed}, Reason: {eval_item.reason}")

                if judge_res.passed:
                    passed += 1
                else:
                    failed += 1

                details.append({
                    "case_id": case_id,
                    "status": "passed" if judge_res.passed else "failed",
                    "passed": judge_res.passed,
                    "rubric_evaluations": [item.model_dump() for item in judge_res.rubric_evaluations]
                })

            accuracy = (passed / total) if total > 0 else 0.0

            # 詳細結果のファイル保存
            detail_file_path = os.path.join(
                os.path.dirname(eval_set_path),
                f"{skill_name}_judge_details.json"
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
            print(f"Unexpected error in JudgeTestExecutor: {e}")
            import traceback
            traceback.print_exc()
            return EvalRunResult(passed=0, failed=1, total=1, accuracy=0.0)