import os
import sys
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from edd_agent_tools.utils.schema import remove_additional_properties

# Pydanticモデル定義
class Parameter(BaseModel):
    name: str = Field(..., description="パラメータの名前")
    type: str = Field(..., description="パラメータの型（例: 'str', 'int', 'bool', 'list'）")
    description: str = Field(..., description="パラメータの説明")
    required: bool = Field(False, description="このパラメータが必須かどうか")
    default: str | None = Field(None, description="パラメータのデフォルト値（任意、文字列として表現）")

class SkillDesign(BaseModel):
    name: str = Field(..., description="スキルの名前")
    parameters: list[Parameter] = Field(..., description="スキルが受け取るパラメータのリスト")
    dependencies: list[str] = Field([], description="スキルが依存する他のスキルのリスト")

def process_message(tool_context: ToolContext):
    """
    skill-designer のメインビジネスロジック。
    自然言語の要件から ADK 2.0 互換の design.json を設計して出力します。
    """
    target_type = tool_context.state.get("target_type")
    name = tool_context.state.get("name")
    requirement = tool_context.state.get("requirement")
    output_dir = tool_context.state.get("output_dir")

    if not all([target_type, name, requirement, output_dir]):
        raise ValueError("target_type, name, requirement, output_dir のいずれか、またはすべてが指定されていません。")

    # パスの補正
    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(os.path.join("/workspace", output_dir))

    # プロンプトアセットのロード
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "..", "assets", "prompt.txt")
    
    assets_dir = os.path.join(script_dir, "..", "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    if not os.path.exists(prompt_path):
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write("あなたは優秀なスキルデザイナーです。以下の機能要件に基づき、ADK 2.0互換のdesign.jsonを設計してください。\n\n機能要件:\nターゲットタイプ: {target_type}\nスキル名: {name}\n要件詳細: {requirement}\n\n設計するdesign.jsonのフォーマットは、Pydanticスキーマとして定義されたSkillDesignクラスに従ってください。\n特にparametersはSkillが受け取る引数を詳細に記述してください。")
            
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_tmpl = f.read()

    formatted_prompt = prompt_tmpl.format(
        target_type=target_type,
        name=name,
        requirement=requirement
    )

    # Gemini API の呼び出し
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が環境変数に設定されていません。")
    
    client = genai.Client(api_key=api_key)
    
    schema_dict = SkillDesign.model_json_schema()
    clean_schema = remove_additional_properties(schema_dict)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=formatted_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=clean_schema,
            temperature=0.1
        )
    )

    # レスポンスのパースとdesign.jsonの保存
    design_data = json.loads(response.text)
    
    output_file_path = os.path.join(output_dir, "design.json")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(design_data, f, indent=2, ensure_ascii=False)

    tool_context.state["status"] = "success"
    tool_context.state["message"] = f"design.json が '{output_file_path}' に正常に生成されました。"
    tool_context.state["output_file_path"] = output_file_path
