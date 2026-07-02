import argparse
import os
import sys
import json
from google import genai
from google.genai import types
from google.adk.tools import ToolContext


# インポートキャッシュの不整合対策
sys.modules.pop('google', None)
sys.modules.pop('google.adk', None)

def generate_test_cases(skill_name: str):
    skill_dir = os.path.join("/workspace/src/skills", skill_name)
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    
    if not os.path.exists(skill_md_path):
        raise FileNotFoundError(f"Error: Skill specification {skill_md_path} not found.")
        
    print(f"Loading skill specification from {skill_md_path}")
    with open(skill_md_path, "r", encoding="utf-8") as f:
        skill_content = f.read()
        
    # Initialize Gemini API Client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Error: GEMINI_API_KEY environment variable is not set.")
        
    client = genai.Client(api_key=api_key)
    
    # Load templates and prompt assets
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, "..", "assets")
    
    prompt_tmpl_path = os.path.join(assets_dir, "test_case_gen_prompt.txt")
    json_tmpl_path = os.path.join(assets_dir, "evalset_template.json")
    
    if not os.path.exists(prompt_tmpl_path) or not os.path.exists(json_tmpl_path):
        raise FileNotFoundError("Error: Template files not found in assets.")
        
    with open(prompt_tmpl_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    with open(json_tmpl_path, "r", encoding="utf-8") as f:
        json_template = f.read()
        
    # json_template 自体に含まれるプレースホルダーを置換
    json_template = json_template.replace(
        "{skill_name_underscore}", skill_name.replace('-', '_')
    ).replace(
        "{skill_name}", skill_name
    )
    
    # プロンプトの組み立て
    prompt = prompt_template.replace(
        "{skill_content}", skill_content
    ).replace(
        "{json_template}", json_template
    )

    print("Generating unit test cases using Gemini API...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )
    
    # 応答をパース
    try:
        test_case_data = json.loads(response.text)
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(response.text)
        raise e
        
    # テストファイルを保存
    tests_dir = os.path.join(skill_dir, "tests")
    os.makedirs(tests_dir, exist_ok=True)
    
    eval_set_filename = f"{skill_name.replace('-', '_')}_eval_set.evalset.json"
    eval_set_path = os.path.join(tests_dir, eval_set_filename)
    
    with open(eval_set_path, "w", encoding="utf-8") as f:
        json.dump(test_case_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated and saved test cases: {eval_set_path}")
    
    # テスト構成ファイルを保存
    config_path = os.path.join(tests_dir, "test_config.json")
    config_data = {
        "eval_set_path": eval_set_path,
        "threshold_accuracy": 1.0
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated and saved test config: {config_path}")


def generate_unit_tests(tool_context: ToolContext) -> str:
    skill_name = tool_context.state.get("skill_name")
    if not skill_name:
        raise ValueError("Error: 'skill_name' is not set in session state.")
        
    generate_test_cases(skill_name)
    
    # 結果パスをセッション状態に保存
    skill_dir = os.path.join("/workspace/src/skills", skill_name)
    eval_set_filename = f"{skill_name.replace('-', '_')}_eval_set.evalset.json"
    eval_set_path = os.path.join(skill_dir, "tests", eval_set_filename)
    
    tool_context.state["eval_set_path"] = eval_set_path
    return f"Success: Unit tests generated at {eval_set_path}"


def main():
    parser = argparse.ArgumentParser(description="Unit Test Case Generator")
    parser.add_argument("--skill_name", type=str, required=True)
    args = parser.parse_args()
    generate_test_cases(args.skill_name)

if __name__ == "__main__":
    main()
