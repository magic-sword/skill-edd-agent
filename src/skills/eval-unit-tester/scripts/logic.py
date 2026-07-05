import os
import json
import re
from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from pydantic import BaseModel, Field, create_model
from edd_agent_tools.registry import SkillRegistry
from .strategy import get_output_mode_strategy
from .models import Input

class TestParameterCase(BaseModel):
    user_instruction: str = Field(
        ...,
        description="ユーザーからの自然言語での指示（例: 『hello worldを大文字にしてください』など）"
    )
    input_parameters: dict = Field(
        ...,
        description="ツールに渡す引数（args）の辞書。キー名は仕様書（SKILL.md）の引数に従ってください。"
    )
    expected_output: str = Field(
        ...,
        description="ツールまたはエージェントからの期待される最終的なテキスト応答（例: 'HELLO WORLD'）"
    )

class TestParameterSet(BaseModel):
    cases: list[TestParameterCase] = Field(
        ...,
        description="生成されたテストパラメータケースのリスト"
    )


def _generate_test_cases(skill: str, registry: SkillRegistry) -> str:
    """
    指定されたスキルに対して評価用の単体テストスイートを生成し、パスを返します。
    """
    skill_dir_obj = registry.get_skill_directory(name=skill)
    skill_dir = skill_dir_obj.root_dir
    skill_content = skill_dir_obj.load_spec()
        
    from edd_agent_tools import GeminiClient
    client = GeminiClient()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, "..", "assets")
    
    prompt_tmpl_path = os.path.join(assets_dir, "test_case_gen_prompt.txt")
    if not os.path.exists(prompt_tmpl_path):
        raise FileNotFoundError("Error: Template file not found in assets.")
        
    with open(prompt_tmpl_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    strategy = get_output_mode_strategy(skill_content)
    instruction_override = strategy.get_instruction_override()

    pydantic_schema_str = ""
    InputSchema = registry.load_input_schema(skill)
    if InputSchema:
        try:
            pydantic_schema_str = json.dumps(InputSchema.model_json_schema(), ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not extract Pydantic schema for {skill}: {e}")
    print(f"DEBUG: Pydantic Schema = {pydantic_schema_str}")

    prompt = prompt_template.replace(
        "{skill_content}", skill_content
    ).replace(
        "{pydantic_schema}", pydantic_schema_str
    ).replace(
        "{instruction_override}", instruction_override
    )

    print("Generating unit test cases using Gemini API...")
    
    TargetSetClass = TestParameterSet
    
    if InputSchema:
        try:
            DynamicTestParameterCase = create_model(
                'DynamicTestParameterCase',
                user_instruction=(str, Field(
                    ...,
                    description="ユーザーからの自然言語での指示（例: 『hello worldを大文字にしてください』など）"
                )),
                input_parameters=(InputSchema, Field(
                    ...,
                    description="ツールに渡す引数のオブジェクト。定義されたスキーマに厳密に従ってください。"
                )),
                expected_output=(str, Field(
                    ...,
                    description="ツールまたはエージェントからの期待される最終的なテキスト応答（例: 'HELLO WORLD'）"
                ))
            )
            DynamicTestParameterSet = create_model(
                'DynamicTestParameterSet',
                cases=(list[DynamicTestParameterCase], Field(
                    ...,
                    description="生成されたテストパラメータケースのリスト"
                ))
            )
            TargetSetClass = DynamicTestParameterSet
        except Exception as e:
            print(f"Warning: Could not create dynamic response schema: {e}")
            TargetSetClass = TestParameterSet

    response = client.generate_content(
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TargetSetClass,
            temperature=0.2
        )
    )
    
    print(f"DEBUG: Gemini Response = {response.text}")
    try:
        parameter_data = json.loads(response.text)
        param_set = TargetSetClass.model_validate(parameter_data)
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(response.text)
        raise e
        
    skill_name_underscore = skill.replace('-', '_')
    # ツール関数名を skill_name_underscore に変更
    tool_function_name = skill_name_underscore
    
    eval_cases = []
    for i, case in enumerate(param_set.cases):
        eval_id = f"{skill_name_underscore}_happy_path_{i+1:03d}"
        
        input_args = case.input_parameters
        if hasattr(input_args, "model_dump"):
            input_args = input_args.model_dump()
        elif not isinstance(input_args, dict):
            input_args = {"text": str(input_args)}

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
                        "name": tool_function_name,  # ここを修正
                        "args": input_args
                    }
                ],
                "tool_responses": [
                    {
                        "name": tool_function_name,  # ここを修正
                        "response": {
                            "result": case.expected_output
                        }
                    }
                ]
            }
        }
        
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
        "name": f"{skill} evaluation set",
        "description": f"{skill} skill unit tests",
        "eval_cases": eval_cases
    }

    eval_set_path = skill_dir_obj.save_eval_set(eval_set_data, test_type="unit")
    print(f"Successfully generated and saved test cases: {eval_set_path}")
    
    # テスト構成ファイルの保存
    config_data = {
        "eval_set_path": eval_set_path,
        "threshold_accuracy": 1.0,
        "criteria": {
            "response_match_score": 0.8
        }
    }
    config_path = skill_dir_obj.save_eval_config(config_data, test_type="unit")
    print(f"Successfully generated and saved test config: {config_path}")
    
    return eval_set_path

def process_message(params: Input, tool_context: ToolContext) -> str:
    """
    指定されたスキルに対して評価用の単体テストスイートを自動生成します。
    """
    skill = params.skill
    if not skill:
        raise ValueError("Error: 'skill' is not set.")
        
    registry = SkillRegistry()
    
    eval_set_path = _generate_test_cases(skill, registry)
    
    # 結果パスをセッション状態に保存
    tool_context.state["eval_set_path"] = eval_set_path
    return f"Success: Unit tests generated at {eval_set_path}"