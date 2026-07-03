import argparse
import json
import os
import sys
from datetime import datetime
from google.adk.tools import ToolContext


# プロジェクトルートをsys.pathに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
sys.path.append(WORKSPACE_ROOT)

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from edd_agent_tools.utils.schema import remove_additional_properties
from edd_agent_tools.testing.cli import SkillCommandLineRunner

class StaticEvalResult(BaseModel):
    specificity: int = Field(..., description="トリガー条件の具体性を1-5の整数で評価したもの")
    clarity: int = Field(..., description="トリガー条件の明確性を1-5の整数で評価したもの")

class PromptItem(BaseModel):
    text: str = Field(..., description="プロンプトのテキスト")

class TriggerTestCases(BaseModel):
    positive_prompts: list[PromptItem] = Field(..., description="このスキルがトリガーされるべき陽性プロンプト（10件）")
    negative_prompts: list[PromptItem] = Field(..., description="このスキルとは関係のない一般的な雑談などの陰性プロンプト（10件）")



# パスの定義
SKILLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# Gemini API の初期化
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。", file=sys.stderr)
    sys.exit(1)
genai_client = genai.Client(api_key=api_key)

def load_file_content(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ファイルが見つかりません: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def save_json_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json_file(filepath, default_value=None):
    if not os.path.exists(filepath):
        return default_value
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def static_evaluate_skill_md(skill_name, skill_md_content):
    """第1ゲート: SKILL.mdの静的評価（具体性、明確性）"""
    print(f"[第1ゲート] スキル '{skill_name}' のSKILL.mdを静的評価中...\n")
    
    static_prompt_path = os.path.join(SCRIPT_DIR, "..", "assets", "static_eval_prompt.txt")
    criteria_path = os.path.join(SCRIPT_DIR, "..", "assets", "eval_criteria.json")
    
    static_eval_prompt_template = load_file_content(static_prompt_path)
    eval_criteria = load_json_file(criteria_path)

    prompt = static_eval_prompt_template.replace(
        "{eval_criteria}", json.dumps(eval_criteria, indent=2, ensure_ascii=False)
    ).replace(
        "{skill_md_content}", skill_md_content
    )

    try:
        schema_dict = StaticEvalResult.model_json_schema()
        clean_schema = remove_additional_properties(schema_dict)

        response = genai_client.models.generate_content(
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

def generate_trigger_test_cases(skill_name, skill_md_content):
    """第2ゲート: トリガー評価用のテストケース自動生成"""
    print(f"[第2ゲート] スキル '{skill_name}' のトリガー評価用テストケースを生成中...\n")
    
    test_gen_prompt_path = os.path.join(SCRIPT_DIR, "..", "assets", "test_case_gen_prompt.txt")
    test_case_gen_prompt_template = load_file_content(test_gen_prompt_path)
    
    prompt = test_case_gen_prompt_template.replace(
        "{skill_name}", skill_name
    ).replace(
        "{skill_md_content}", skill_md_content
    )

    try:
        schema_dict = TriggerTestCases.model_json_schema()
        clean_schema = remove_additional_properties(schema_dict)

        response = genai_client.models.generate_content(
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
        for i, p_prompt in enumerate(generated_cases.get("positive_prompts", [])):
            text = p_prompt.get("text", "")
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
            
        for i, n_prompt in enumerate(generated_cases.get("negative_prompts", [])):
            text = n_prompt.get("text", "")
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

        # 保存先は対象スキルの tests/ ディレクトリ
        skill_tests_dir = os.path.join(SKILLS_DIR, skill_name, "tests")
        os.makedirs(skill_tests_dir, exist_ok=True)
        
        eval_set_filepath = os.path.join(skill_tests_dir, f"{skill_name}_trigger_eval.evalset.json")
        config_filepath = os.path.join(skill_tests_dir, f"{skill_name}_trigger_eval.evalset.config.json")
        
        save_json_file(eval_set_filepath, eval_set_data)
        save_json_file(config_filepath, config_data)
        
        print(f"  - テストケースを '{eval_set_filepath}' に保存しました。")
        print(f"  - 評価設定を '{config_filepath}' に保存しました。\n")
        return eval_set_filepath
    except Exception as e:
        print(f"  => テストケース生成中にエラーが発生しました: {e}\n")
        return None

def save_report(skill_name, static_eval_result, generated_cases_file):
    """詳細レポートを保存します。"""
    now_str = datetime.now().isoformat() + "Z"
    
    report_filepath = os.path.join(SKILLS_DIR, skill_name, "tests", "trigger_eval_report.json")
    report_data = {
        "skill_name": skill_name,
        "static_evaluation": static_eval_result,
        "generated_cases_file": generated_cases_file,
        "status": "PASSED" if static_eval_result.get("passed") else "FAILED",
        "evaluation_date": now_str
    }
    save_json_file(report_filepath, report_data)
    print(f"  - 詳細レポートを '{report_filepath}' に保存しました。\n")

def execute_trigger_logic(tool_context: ToolContext):
    """トリガー評価・生成のメインビジネスロジック"""
    skill_name = tool_context.state.get("skill_name")
    if not skill_name:
        raise ValueError("エラー: skill_name がセッション状態に設定されていません。")
        
    skill_md_filepath = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    
    print(f"スキル '{skill_name}' のトリガーアセット生成を開始します。\n")

    status = "success"
    message = "Successfully generated trigger test assets."
    eval_set_filepath = ""

    try:
        try:
            skill_md_content = load_file_content(skill_md_filepath)
        except FileNotFoundError:
            raise FileNotFoundError(f"対象スキル '{skill_name}' のSKILL.mdファイルが見つかりません: {skill_md_filepath}")

        # 第1ゲート: 静的評価
        static_eval_result = static_evaluate_skill_md(skill_name, skill_md_content)
        if not static_eval_result["passed"]:
            raise ValueError(f"トリガー静的評価不合格 (Specificity: {static_eval_result.get('specificity')}, Clarity: {static_eval_result.get('clarity')})")

        # 第2ゲート: テストケース生成
        eval_set_filepath = generate_trigger_test_cases(skill_name, skill_md_content)
        if not eval_set_filepath:
            raise ValueError("テストケース生成に失敗しました。")

        # 全体合格とレポート保存
        print(f"🎉 スキル '{skill_name}' のトリガー評価用テストアセットを正常に生成しました！")
        save_report(skill_name, static_eval_result, eval_set_filepath)
        print("アセット生成プロセスが正常に完了しました。")
    except Exception as e:
        status = "failed"
        message = str(e)
        print(f"❌ エラー: {e}", file=sys.stderr)

    # 共通の出力状態のセット
    tool_context.state.update({
        "status": status,
        "message": message,
        "eval_set_path": eval_set_filepath
    })

    if status == "success":
        tool_context.state["trig_eval_set_path"] = eval_set_filepath
    else:
        raise RuntimeError(message)

def generate_trigger_tests(tool_context: ToolContext) -> str:
    """
    指定されたスキル（skill_name）に対するトリガーテストケースを自動生成し、
    結果を trig_eval_set_path に保存します。
    """
    execute_trigger_logic(tool_context)
    
    # ワークフロー用の固有一時フォルダへの書き出し (互換性のため)
    skill_name = tool_context.state.get("skill_name")
    output_json_path = f"/workspace/src/.workflow_tmp/{skill_name}/05_trig_gen_out.json"
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": tool_context.state.get("status"),
            "message": tool_context.state.get("message"),
            "eval_set_path": tool_context.state.get("eval_set_path")
        }, f, indent=2, ensure_ascii=False)
        
    return f"Success: Generated trigger tests at '{tool_context.state.get('eval_set_path')}'."

if __name__ == "__main__":
    runner = SkillCommandLineRunner(description="指定されたスキルのトリガー定義の品質チェックとテスト生成を行います。")
    runner.add_argument("--skill_name", help="評価対象のスキル名")
    runner.run(execute_trigger_logic)
