import argparse
import json
import os
import sys
from datetime import datetime

# プロジェクトルートをsys.pathに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
sys.path.append(WORKSPACE_ROOT)

import google
import google.auth
google.auth = google.auth

from google import genai
from google.genai import types
from pydantic import BaseModel

# パスの定義
# /workspace/src/skills/trigger-evaluator/scripts -> /workspace/src/skills_registry.json
REGISTRY_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "skills_registry.json"))
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
        class StaticScore(BaseModel):
            specificity: int
            clarity: int

        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
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
    """第2ゲート前半: トリガー評価用のテストケース自動生成"""
    print(f"[第2ゲート] スキル '{skill_name}' のトリガー評価用テストケースを生成中...\n")
    
    test_gen_prompt_path = os.path.join(SCRIPT_DIR, "..", "assets", "test_case_gen_prompt.txt")
    test_case_gen_prompt_template = load_file_content(test_gen_prompt_path)
    
    prompt = test_case_gen_prompt_template.replace(
        "{skill_name}", skill_name
    ).replace(
        "{skill_md_content}", skill_md_content
    )

    try:
        class PromptSet(BaseModel):
            positive_prompts: list[dict]
            negative_prompts: list[dict]

        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
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

        eval_set_filepath = f"tests/{skill_name}_trigger_eval.evalset.json"
        config_filepath = f"tests/{skill_name}_trigger_eval.evalset.config.json"
        
        save_json_file(eval_set_filepath, eval_set_data)
        save_json_file(config_filepath, config_data)
        
        print(f"  - テストケースを '{eval_set_filepath}' に保存しました。\n")
        return eval_set_filepath
    except Exception as e:
        print(f"  => テストケース生成中にエラーが発生しました: {e}\n")
        return None

def run_agent_evaluation(skill_name, eval_set_filepath):
    """第2ゲート後半: adk eval CLI を別プロセス(env -i)で起動して、合格・不合格数から精度を算出"""
    print(f"[第2ゲート] スキル '{skill_name}' の動的評価を実行中...\n")

    try:
        import subprocess
        import re
        
        config_filepath = f"tests/{skill_name}_trigger_eval.evalset.config.json"
        
        # メモリ共有やインポートロックを完全に防ぐため、env -i でOSレベルのプロセス分離を行う
        cmd = [
            "env", "-i",
            "HOME=/home/vscode",
            "LANG=C.UTF-8",
            "PATH=/workspace/.venv/bin:/usr/local/bin:/usr/bin:/bin",
            f"GEMINI_API_KEY={os.environ.get('GEMINI_API_KEY', '')}",
            "ADK_EVAL_MODE=1",  # 評価モード(EnvironmentToolsetの無効化)
            "/workspace/.venv/bin/adk",
            "eval", "/workspace/src", eval_set_filepath,
            "--config_file_path", config_filepath
        ]
        
        print("  - サブプロセス評価を実行中 (タイムアウト制限: 180秒)...")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3分の強制タイムアウト
            )
        except subprocess.TimeoutExpired as te:
            raise RuntimeError("評価実行中にタイムアウトが発生しました。デッドロックまたは無限ループの可能性があります。") from te
            
        output = result.stdout
        err_output = result.stderr
        
        print(f"--- CLI出力 ---\n{output}\n----------------")
        if err_output:
            print(f"--- エラー出力 ---\n{err_output}\n----------------")

        passed_match = re.search(r"Tests\s+passed:\s*(\d+)", output)
        failed_match = re.search(r"Tests\s+failed:\s*(\d+)", output)
        
        if not passed_match or not failed_match:
            raise RuntimeError(f"CLI出力からテスト結果数を抽出できませんでした。CLI出力:\n{output}\n[標準エラー出力]:\n{err_output}")
            
        passed_cases = int(passed_match.group(1))
        failed_cases = int(failed_match.group(1))
        total_cases = passed_cases + failed_cases
        
        accuracy = passed_cases / total_cases if total_cases > 0 else 0.0
        print(f"  - 評価結果: {passed_cases}/{total_cases} ケース合格 (精度: {accuracy:.2%})")

        details = []
        for i in range(passed_cases):
            details.append({"eval_id": f"case_{i}", "passed": True})
        for i in range(failed_cases):
            details.append({"eval_id": f"failed_case_{i}", "passed": False})

        if accuracy >= 0.90:
            print("  => 動的評価: 合格 (精度 >= 90%)\n")
            return {"accuracy": accuracy, "passed": True, "details": details}
        else:
            print("  => 動的評価: 不合格 (精度 < 90%)\n")
            return {"accuracy": accuracy, "passed": False, "details": details}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  => 動的評価中にエラーが発生しました: {e}\n")
        return {"accuracy": 0.0, "passed": False, "error": str(e), "details": []}

def update_registry_and_report(skill_name, static_eval_result, dynamic_eval_result, overall_status):
    """中央レジストリと詳細レポートを更新します。"""
    print("評価結果を保存中...\n")

    registry = load_json_file(REGISTRY_PATH, default_value={"skills": {}})
    
    if "skills" not in registry:
        registry["skills"] = {}
        
    now_str = datetime.now().isoformat() + "Z"
    
    if skill_name not in registry["skills"]:
        registry["skills"][skill_name] = {
            "tier": 1,
            "last_tested": now_str,
            "file_hashes": {}
        }
    
    registry["skills"][skill_name]["trigger_eval_status"] = "PASSED" if overall_status else "FAILED"
    registry["skills"][skill_name]["trigger_eval_accuracy"] = dynamic_eval_result.get("accuracy", 0.0)
    registry["skills"][skill_name]["last_eval_date"] = now_str
    
    save_json_file(REGISTRY_PATH, registry)
    print(f"  - 中央レジストリ '{REGISTRY_PATH}' を更新しました。")

    # 詳細レポートの保存
    report_filepath = os.path.join(SKILLS_DIR, skill_name, "tests", "trigger_eval_report.json")
    report_data = {
        "skill_name": skill_name,
        "static_evaluation": static_eval_result,
        "dynamic_evaluation": dynamic_eval_result,
        "overall_status": "PASSED" if overall_status else "FAILED",
        "evaluation_date": now_str
    }
    save_json_file(report_filepath, report_data)
    print(f"  - 詳細レポートを '{report_filepath}' に保存しました。\n")

def main():
    parser = argparse.ArgumentParser(description="指定されたスキルのトリガー定義の品質と精度を評価します。")
    parser.add_argument("--skill_name", required=True, help="評価対象のスキル名（例: my-awesome-skill）")
    args = parser.parse_args()

    skill_name = args.skill_name
    skill_md_filepath = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    
    print(f"スキル '{skill_name}' のトリガー評価を開始します。\n")

    try:
        skill_md_content = load_file_content(skill_md_filepath)
    except FileNotFoundError:
        print(f"エラー: 対象スキル '{skill_name}' のSKILL.mdファイルが見つかりません: {skill_md_filepath}", file=sys.stderr)
        sys.exit(1)

    # 第1ゲート: 静的評価
    static_eval_result = static_evaluate_skill_md(skill_name, skill_md_content)
    if not static_eval_result["passed"]:
        print(f"スキル '{skill_name}' のトリガー評価は不合格でした (静的評価ゲートで失敗)。")
        update_registry_and_report(skill_name, static_eval_result, {"accuracy": 0.0, "passed": False, "details": []}, False)
        sys.exit(0)

    # 第2ゲート前半: テストケース生成
    eval_set_filepath = generate_trigger_test_cases(skill_name, skill_md_content)
    if not eval_set_filepath:
        print(f"スキル '{skill_name}' のトリガー評価は不合格でした (テストケース生成で失敗)。")
        update_registry_and_report(skill_name, static_eval_result, {"accuracy": 0.0, "passed": False, "details": []}, False)
        sys.exit(0)

    # 第2ゲート後半: 動的評価
    dynamic_eval_result = run_agent_evaluation(skill_name, eval_set_filepath)
    if not dynamic_eval_result["passed"]:
        print(f"スキル '{skill_name}' のトリガー評価は不合格でした (動的評価ゲートで失敗)。")
        update_registry_and_report(skill_name, static_eval_result, dynamic_eval_result, False)
        sys.exit(0)

    # 全体合格
    print(f"スキル '{skill_name}' のトリガー評価は合格しました！")
    update_registry_and_report(skill_name, static_eval_result, dynamic_eval_result, True)
    print("評価プロセスが正常に完了しました。")

if __name__ == "__main__":
    main()
