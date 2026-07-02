import argparse
import os
import sys
import json
from google import genai
from google.genai import types

def generate_test_cases(skill_name: str):
    skill_dir = os.path.join("/workspace/src/skills", skill_name)
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    
    if not os.path.exists(skill_md_path):
        raise FileNotFoundError(f"エラー: スキル仕様書 {skill_md_path} が見つかりません。")
        
    print(f"Loading skill specification from {skill_md_path}")
    with open(skill_md_path, "r", encoding="utf-8") as f:
        skill_content = f.read()
        
    # Gemini API クライアントの初期化
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("エラー: GEMINI_API_KEY 環境変数が設定されていません。")
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
あなたはGoogle ADK (Antigravity) 2.0のテストアセット生成のスペシャリストです。
提供された以下のスキルの仕様書（SKILL.md）を読み、このスキルの動作を確認するための代表的なテストケース（単体テスト）を 4件〜6件 生成してください。

【対象スキルの仕様書】
{skill_content}

【JSONスキーマの要件】
生成するJSONは、以下の構造に完全に適合していなければなりません。
```json
{{
  "eval_set_id": "{skill_name.replace('-', '_')}_eval_set",
  "name": "{skill_name} evaluation set",
  "description": "{skill_name} skill unit tests",
  "eval_cases": [
    {{
      "eval_id": "テストケースの一意なID (例: to_upper_001)",
      "conversation": [
        {{
          "invocation_id": "一意の呼び出しID (例: inv_1)",
          "user_content": {{
            "role": "user",
            "parts": [
              {{
                "text": "ユーザーの入力プロンプト"
              }}
            ]
          }},
          "final_response": {{
            "role": "model",
            "parts": [
              {{
                "text": "期待されるモデルの最終出力テキスト（golden answer）"
              }}
            ]
          }},
          "intermediate_data": {{
            "tool_uses": [],
            "intermediate_responses": []
          }}
        }}
      ],
      "session_input": {{
        "app_name": "src",
        "user_id": "test_user",
        "state": {{}}
      }}
    }}
  ]
}}
```

※ intermediate_data.tool_uses や intermediate_data.intermediate_responses は空のリスト [] にしてください。
* 期待される最終出力（final_response.parts[0].text）は、仕様書に合致する正確なものである必要があります。
"""

    print("Generating unit test cases using Gemini API...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    
    test_cases_json = json.loads(response.text)
    
    # 保存先ディレクトリの作成保証
    tests_dir = os.path.join(skill_dir, "tests")
    os.makedirs(tests_dir, exist_ok=True)
    
    # テストファイルの保存
    eval_set_filename = f"{skill_name.replace('-', '_')}_eval_set.evalset.json"
    eval_set_path = os.path.join(tests_dir, eval_set_filename)
    
    with open(eval_set_path, "w", encoding="utf-8") as f:
        json.dump(test_cases_json, f, indent=2, ensure_ascii=False)
        
    print(f"🎉 テストケースファイルを正常に生成し保存しました: {eval_set_path}")
    
    # test_config.json の作成 (ツール軌跡の無視、応答テキスト一致のみを検証する設定)
    config_path = os.path.join(tests_dir, "test_config.json")
    config_data = {
        "criteria": {
            "tool_trajectory_avg_score": 0.0,
            "response_match_score": 0.8
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        
    print(f"🎉 評価設定ファイルを正常に生成し保存しました: {config_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate unit test cases for a skill using Gemini API.")
    parser.add_argument("--skill_name", required=True, help="The name of the skill to generate test cases for.")
    parser.add_argument("--output_json", help="Path to output JSON file")
    args = parser.parse_args()
    
    skill_name = args.skill_name
    status = "success"
    message = "Successfully generated unit test cases."
    eval_set_path = ""
    
    try:
        generate_test_cases(skill_name)
        eval_set_filename = f"{skill_name.replace('-', '_')}_eval_set.evalset.json"
        eval_set_path = os.path.abspath(os.path.join("/workspace/src/skills", skill_name, "tests", eval_set_filename))
    except Exception as e:
        status = "failed"
        message = str(e)
        print(f"Error: {e}", file=sys.stderr)
        
    if args.output_json:
        try:
            out_dir = os.path.dirname(os.path.abspath(args.output_json))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.output_json, "w", encoding="utf-8") as f:
                json.dump({
                    "status": status,
                    "message": message,
                    "skill_name": skill_name,
                    "eval_set_path": eval_set_path
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing output_json: {e}", file=sys.stderr)
            
    if status == "failed":
        sys.exit(1)

if __name__ == "__main__":
    main()
