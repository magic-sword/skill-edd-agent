import json
import os
import sys
from datetime import datetime
from google.adk.tools import ToolContext
from google.genai import types
from edd_agent_tools.utils.schema import remove_additional_properties
from edd_agent_tools.registry import SkillRegistry
from edd_agent_tools.gemini import get_gemini_client
from .models import StaticEvalResult, TriggerTestCases

class TriggerEvaluator:
    def __init__(self, tool_context: ToolContext, genai_client):
        self.tool_context = tool_context
        self.genai_client = genai_client
        self.registry = SkillRegistry()
        self.registry.load()
        # 自身のSkillDirectoryの解決
        self.self_dir = self.registry.get_skill_directory(name="trigger-evaluator")

    def execute(self):
        skill_name = self.tool_context.state.get("skill_name")
        if not skill_name:
            raise ValueError("エラー: skill_name がセッション状態に設定されていません。")

        # 対象スキルのSkillDirectory
        try:
            target_dir = self.registry.get_skill_directory(name=skill_name)
        except Exception as e:
            raise FileNotFoundError(f"対象スキル '{skill_name}' が見つかりません: {e}")

        print(f"スキル '{skill_name}' のトリガーアセット生成を開始します。\n")

        status = "success"
        message = "Successfully generated trigger test assets."
        eval_set_filepath = ""

        try:
            # SKILL.md のロード
            try:
                skill_md_content = target_dir.load_spec()
            except FileNotFoundError as e:
                raise FileNotFoundError(f"対象スキル '{skill_name}' のSKILL.mdファイルが見つかりません: {e}")

            # 第1ゲート: 静的評価
            static_eval_result = self.static_evaluate_skill_md(skill_name, skill_md_content)
            if not static_eval_result["passed"]:
                raise ValueError(f"トリガー静的評価不合格 (Specificity: {static_eval_result.get('specificity')}, Clarity: {static_eval_result.get('clarity')})")

            # 第2ゲート: テストケース生成
            eval_set_filepath = self.generate_trigger_test_cases(skill_name, skill_md_content, target_dir)
            if not eval_set_filepath:
                raise ValueError("テストケース生成に失敗しました。")

            # 全体合格とレポート保存
            print(f"🎉 スキル '{skill_name}' のトリガー評価用テストアセットを正常に生成しました！")
            self.save_report(skill_name, static_eval_result, eval_set_filepath, target_dir)
            print("アセット生成プロセスが正常に完了しました。")

        except Exception as e:
            status = "failed"
            message = str(e)
            print(f"❌ エラー: {e}", file=sys.stderr)

        # 共通の出力状態のセット
        self.tool_context.state.update({
            "status": status,
            "message": message,
            "eval_set_path": eval_set_filepath
        })

        if status == "success":
            self.tool_context.state["trig_eval_set_path"] = eval_set_filepath
            # ワークフロー用の固固有時フォルダへの書き出し (互換性のため)
            output_json_path = f"/workspace/src/.workflow_tmp/{skill_name}/05_trig_gen_out.json"
            os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "status": status,
                    "message": message,
                    "eval_set_path": eval_set_filepath
                }, f, indent=2, ensure_ascii=False)
        else:
            raise RuntimeError(message)

    def static_evaluate_skill_md(self, skill_name: str, skill_md_content: str) -> dict:
        """第1ゲート: SKILL.mdの静的評価（具体性、明確性）"""
        print(f"[第1ゲート] スキル '{skill_name}' のSKILL.mdを静的評価中...\n")

        # アセットのロード (os.path.joinのハードコード全廃)
        static_prompt_template = self.self_dir.load_asset("static_eval_prompt.txt")
        eval_criteria_str = self.self_dir.load_asset("eval_criteria.json")
        eval_criteria = json.loads(eval_criteria_str)

        prompt = static_prompt_template.replace(
            "{eval_criteria}", json.dumps(eval_criteria, indent=2, ensure_ascii=False)
        ).replace(
            "{skill_md_content}", skill_md_content
        )

        try:
            schema_dict = StaticEvalResult.model_json_schema()
            clean_schema = remove_additional_properties(schema_dict)

            response = self.genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=clean_schema,
                    temperature=0.1
                )
            )
            eval_result = json.loads(response.text)
            specificity = eval_result.get("specificity", 0)
            clarity = eval_result.get("clarity", 0)

            print(f"  - 具体性 (Specificity): {specificity}/5")
            print(f"  - 明確性 (Clarity): {clarity}/5")

            if specificity >= 4 and clarity >= 4:
                print("  => 静的評価: 合格 (Specificity >= 4, Clarity >= 4)\n")
                return {"specificity": specificity, "clarity": clarity, "passed": True}
            else:
                print("  => 静的評価: 不合格 (Specificity < 4 または Clarity < 4)\n")
                return {"specificity": specificity, "clarity": clarity, "passed": False}
        except Exception as e:
            print(f"  => 静的評価中にエラーが発生しました: {e}\n")
            return {"specificity": 0, "clarity": 0, "passed": False, "error": str(e)}

    def generate_trigger_test_cases(self, skill_name: str, skill_md_content: str, target_dir) -> str:
        """第2ゲート: トリガー評価用のテストケース自動生成"""
        print(f"[第2ゲート] スキル '{skill_name}' のトリガー評価用テストケースを生成中...\n")

        test_gen_prompt_template = self.self_dir.load_asset("test_case_gen_prompt.txt")

        prompt = test_gen_prompt_template.replace(
            "{skill_name}", skill_name
        ).replace(
            "{skill_md_content}", skill_md_content
        )

        try:
            schema_dict = TriggerTestCases.model_json_schema()
            clean_schema = remove_additional_properties(schema_dict)

            response = self.genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=clean_schema,
                    temperature=0.2
                )
            )
            generated_cases = json.loads(response.text)

            eval_cases = []
            for i, item in enumerate(generated_cases.get("positive_prompts", [])):
                text = item.get("text", "") if isinstance(item, dict) else str(item)
                eval_cases.append({
                    "eval_id": f"positive_{i+1}",
                    "conversation": [
                        {
                            "invocation_id": f"inv_pos_{i+1}",
                            "user_content": {"parts": [{"text": text}], "role": "user"},
                            "final_response": {
                                "parts": [{"text": "Dummy"}], 
                                "role": "model"
                            },
                            "intermediate_data": {
                                "tool_uses": [
                                    {
                                        "name": "load_skill",
                                        "args": {
                                            "skill_name": skill_name
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "session_input": {"app_name": "evaluation_driven_development_agent", "user_id": "user"}
                })
                
            for i, item in enumerate(generated_cases.get("negative_prompts", [])):
                text = item.get("text", "") if isinstance(item, dict) else str(item)
                eval_cases.append({
                    "eval_id": f"negative_{i+1}",
                    "conversation": [
                        {
                            "invocation_id": f"inv_neg_{i+1}",
                            "user_content": {"parts": [{"text": text}], "role": "user"},
                            "final_response": {
                                "parts": [{"text": "Dummy"}], 
                                "role": "model"
                            },
                            "intermediate_data": {
                                "tool_uses": []
                            }
                        }
                    ],
                    "session_input": {"app_name": "evaluation_driven_development_agent", "user_id": "user"}
                })

            eval_set_data = {
                "eval_set_id": f"{skill_name}_trigger_eval_set",
                "name": f"{skill_name} Trigger Evaluation Set",
                "eval_cases": eval_cases
            }

            config_data = {
                "criteria": {
                    "tool_trajectory_avg_score": {
                        "threshold": 1.0,
                        "match_type": "ANY_ORDER"
                    }
                }
            }

            # 保存
            eval_set_filepath = target_dir.save_eval_set(eval_set_data, test_type="trigger")
            config_filepath = target_dir.save_eval_config(config_data, test_type="trigger")
            
            print(f"  - テストケースを '{eval_set_filepath}' に保存しました。")
            print(f"  - 評価設定を '{config_filepath}' に保存しました。\n")
            return eval_set_filepath
        except Exception as e:
            print(f"  => テストケース生成中にエラーが発生しました: {e}\n")
            return None

    def save_report(self, skill_name: str, static_eval_result: dict, generated_cases_file: str, target_dir):
        """詳細レポートを保存します。"""
        now_str = datetime.now().isoformat() + "Z"
        report_filepath = os.path.join(target_dir.root_dir, "tests", "trigger_eval_report.json")
        report_data = {
            "skill_name": skill_name,
            "static_evaluation": static_eval_result,
            "generated_cases_file": generated_cases_file,
            "status": "PASSED" if static_eval_result.get("passed") else "FAILED",
            "evaluation_date": now_str
        }
        os.makedirs(os.path.dirname(report_filepath), exist_ok=True)
        with open(report_filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"  - 詳細レポートを '{report_filepath}' に保存しました。\n")

def process_message(tool_context: ToolContext):
    genai_client = get_gemini_client()
    evaluator = TriggerEvaluator(tool_context, genai_client)
    evaluator.execute()
