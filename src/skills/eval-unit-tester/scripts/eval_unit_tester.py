import argparse
import os
import sys
import json
import re
from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from pydantic import BaseModel, Field
from edd_agent_tools.utils.schema import remove_additional_properties

from edd_agent_tools.registry import SkillRegistry

# インポートキャッシュの不整合対策
sys.modules.pop('google', None)

class TestParameterCase(BaseModel):
    user_instruction: str = Field(
        ...,
        description="ユーザーからの自然言語での指示（例: 『hello worldを大文字にしてください』など）",
        examples=["「hello world」を大文字に変換し、結果のテキストのみを出力してください。"]
    )
    input_parameters: dict = Field(
        ...,
        description="ツールに渡す引数（args）の辞書。キー名は仕様書（SKILL.md）の引数に従ってください。",
        examples=[{"text": "hello world"}]
    )
    expected_output: str = Field(
        ...,
        description="ツールまたはエージェントからの期待される最終的なテキスト応答（例: 'HELLO WORLD'）",
        examples=["HELLO WORLD"]
    )

class TestParameterSet(BaseModel):
    cases: list[TestParameterCase] = Field(
        ...,
        description="生成されたテストパラメータケースのリスト",
        examples=[
            [
                {
                    "user_instruction": "「hello world」を大文字に変換し、結果のテキストのみを出力してください。",
                    "input_parameters": {"text": "hello world"},
                    "expected_output": "HELLO WORLD"
                }
            ]
        ]
    )



def get_skill_main_function(skill_dir: str) -> str:
    """スキルの main.py から runner.run にバインドされているエントリーポイント関数名を決定論的に抽出します。"""
    main_py_path = os.path.join(skill_dir, "scripts", "main.py")
    if not os.path.exists(main_py_path):
        main_py_path = os.path.join(skill_dir, "main.py")
        
    if os.path.exists(main_py_path):
        with open(main_py_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r'runner\.run\(([^)]+)\)', content)
        if match:
            return match.group(1).strip()
            
    # フォールバック: スキル名のハイフンをアンダースコアにしたもの
    return os.path.basename(skill_dir).replace("-", "_")


def generate_test_cases(skill_name: str):
    registry = SkillRegistry()
    registry.load()
    skill_dir = registry.get_skill_dir(skill_name)
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
    if not os.path.exists(prompt_tmpl_path):
        raise FileNotFoundError("Error: Template file not found in assets.")
        
    with open(prompt_tmpl_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    # 決定論的な仕様スキャン
    is_value_only = "Output Mode: VALUE_ONLY" in skill_content
    is_conversational = "Output Mode: CONVERSATIONAL" in skill_content
    is_structured_json = "Output Mode: STRUCTURED_JSON" in skill_content
    
    # デフォルトは VALUE_ONLY
    if not (is_value_only or is_conversational or is_structured_json):
        is_value_only = True
        
    # Output Mode に応じたプロンプトの動的合成
    if is_value_only:
        instruction_override = (
            "会話内のユーザー入力には必ず「〜〜の結果のみを出力してください」という制約を含め、"
            "期待応答（expected_output）は余計な解説を一切排した結果そのもの（例: 大文字化されたテキストのみ）としてください。"
        )
    elif is_conversational:
        instruction_override = (
            "会話内のユーザー入力は自然なメッセージ（制約なし）とし、期待応答（expected_output）は"
            "ユーザーに対する自然な対話応答メッセージ（例: 「〜〜を処理しました。結果は〜〜です。」など）としてください。"
        )
    elif is_structured_json:
        instruction_override = (
            "期待応答（expected_output）は余計な解説を一切排した生の JSON 文字列（例: {\"result_message\": \"〜〜\"}）"
            "のみとし、自然言語テキストは絶対に含めないでください。"
        )

    # プロンプトの組み立て
    prompt = prompt_template.replace(
        "{skill_content}", skill_content
    ).replace(
        "{instruction_override}", instruction_override
    )


    print("Generating unit test cases using Gemini API...")
    
    # response_schema のクレンジング
    schema_dict = TestParameterSet.model_json_schema()
    clean_schema = remove_additional_properties(schema_dict)

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=clean_schema,
            temperature=0.2
        )
    )
    
    # 応答をパース
    try:
        parameter_data = json.loads(response.text)
        param_set = TestParameterSet.model_validate(parameter_data)
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(response.text)
        raise e
        
    # 決定論的にエントリーポイント関数名を特定
    main_function_name = get_skill_main_function(skill_dir)
    skill_name_underscore = skill_name.replace('-', '_')
    
    # ADK 2.0 の .evalset.json 構造へ組み立てる
    eval_cases = []
    for i, case in enumerate(param_set.cases):
        eval_id = f"{skill_name_underscore}_happy_path_{i+1:03d}"
        
        # args の型が辞書であることを保証
        input_args = case.input_parameters
        if not isinstance(input_args, dict):
            input_args = {"text": str(input_args)}

        # 1ターン分の対話ターンをビルド
        conversation_turn = {
            "invocation_id": f"inv_{i+1:03d}",
            "user_content": {
                "role": "user",
                "parts": [
                    {
                        "text": case.user_instruction
                    }
                ]
            },
            "final_response": {
                "role": "model",
                "parts": [
                    {
                        "text": case.expected_output
                    }
                ]
            },
            "intermediate_data": {
                "tool_uses": [
                    {
                        "name": main_function_name,
                        "args": input_args
                    }
                ],
                "tool_responses": [
                    {
                        "name": main_function_name,
                        "response": {
                            "result": case.expected_output
                        }
                    }
                ]
            }
        }
        
        # セッション初期状態
        session_input = {
            "appName": "src",
            "userId": "test_user",
            "state": input_args
        }
        
        eval_case = {
            "eval_id": eval_id,
            "conversation": [conversation_turn],
            "session_input": session_input
        }
        eval_cases.append(eval_case)
        
    eval_set_data = {
        "eval_set_id": f"{skill_name_underscore}_eval_set",
        "name": f"{skill_name} evaluation set",
        "description": f"{skill_name} skill unit tests",
        "eval_cases": eval_cases
    }

    # テストファイルを保存
    tests_dir = os.path.join(skill_dir, "tests")
    os.makedirs(tests_dir, exist_ok=True)
    
    eval_set_filename = f"{skill_name.replace('-', '_')}_eval_set.evalset.json"
    eval_set_path = os.path.join(tests_dir, eval_set_filename)
    
    with open(eval_set_path, "w", encoding="utf-8") as f:
        json.dump(eval_set_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated and saved test cases: {eval_set_path}")
    
    # テスト構成ファイルを保存
    config_path = os.path.join(tests_dir, "test_config.json")
    config_data = {
        "eval_set_path": eval_set_path,
        "threshold_accuracy": 1.0,
        "criteria": {
            "response_match_score": 0.8
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated and saved test config: {config_path}")


def execute_unit_tester_logic(tool_context: ToolContext):
    """単体テスト生成のメインビジネスロジック"""
    skill_name = tool_context.state.get("skill_name")
    if not skill_name:
        raise ValueError("Error: 'skill_name' is not set.")
        
    generate_test_cases(skill_name)
    
    # 結果パスをセッション状態に保存
    registry = SkillRegistry()
    registry.load()
    skill_dir = registry.get_skill_dir(skill_name)
    eval_set_filename = f"{skill_name.replace('-', '_')}_eval_set.evalset.json"
    eval_set_path = os.path.join(skill_dir, "tests", eval_set_filename)
    
    tool_context.state["eval_set_path"] = eval_set_path

def generate_unit_tests(tool_context: ToolContext) -> str:
    """
    指定されたスキルのテストを実行します。
    """
    execute_unit_tester_logic(tool_context)
    return f"Success: Unit tests generated at {tool_context.state.get('eval_set_path')}"
