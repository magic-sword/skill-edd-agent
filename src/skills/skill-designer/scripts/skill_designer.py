import os
import sys
import json
from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from edd_agent_tools.utils.schema import remove_additional_properties
from edd_agent_tools.models import SkillDesign

def process_message(tool_context: ToolContext):
    """
    skill-designer のメインビジネスロジック。
    自然言語の要件や既存のソースコードから ADK 2.0 互換の design.json を設計して出力します。
    """
    requirement = tool_context.state.get("requirement")
    output_dir = tool_context.state.get("output_dir")
    source_code_path = tool_context.state.get("source_code_path")

    if not all([requirement, output_dir]):
        raise ValueError("requirement, output_dir のいずれか、またはすべてが指定されていません。")

    # パスの補正
    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(os.path.join("/workspace", output_dir))

    # ソースコードパスの自動検知
    if not source_code_path and output_dir:
        scripts_dir = os.path.join(output_dir, "scripts")
        if os.path.exists(scripts_dir):
            py_files = [f for f in os.listdir(scripts_dir) if f.endswith(".py") and f != "__init__.py"]
            if "main.py" in py_files:
                source_code_path = os.path.join(scripts_dir, "main.py")
            elif len(py_files) == 1:
                source_code_path = os.path.join(scripts_dir, py_files[0])

    # ソースコードパスの絶対パス解決
    if source_code_path and not os.path.isabs(source_code_path):
        source_code_path = os.path.abspath(os.path.join("/workspace", source_code_path))

    # 既存のスキル名の特定 (再設計時に元の名前を決定論的に強制するため)
    existing_name = None
    
    # 1. 既存のソースコードパスの親階層から抽出 (最も確実)
    if source_code_path and os.path.exists(source_code_path):
        comp_root = os.path.dirname(os.path.dirname(source_code_path))
        if os.path.basename(comp_root) not in ["", ".", ".."]:
            existing_name = os.path.basename(comp_root)

    # 2. 既存の design.json から取得
    if not existing_name:
        existing_design_paths = [
            os.path.join(output_dir, "assets", "design.json"),
            os.path.join(output_dir, "design.json")
        ]
        for p in existing_design_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        old_data = json.load(f)
                        if isinstance(old_data, dict) and old_data.get("name"):
                            existing_name = old_data["name"]
                            break
                except Exception:
                    pass

    # 3. 既存の出力先フォルダ名から取得
    if not existing_name and os.path.exists(output_dir) and os.path.basename(output_dir) not in ["", ".", ".."]:
        existing_name = os.path.basename(output_dir)

    # 既存のソースコードのロード
    source_code = ""
    if source_code_path and os.path.exists(source_code_path):
        print(f"Automatically detected existing source code path: {source_code_path}")
        with open(source_code_path, "r", encoding="utf-8") as f:
            source_code = f.read()

    # プロンプトアセットのロード
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "..", "assets", "prompt.txt")
    
    assets_dir = os.path.join(script_dir, "..", "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    if not os.path.exists(prompt_path):
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write("あなたは優秀なスキルデザイナーです。以下の情報に基づき、ADK 2.0互換 of design.jsonを設計してください。\n\n要件詳細:\n{requirement}\n\n[既存の実装コード]\n{implementation_code}\n\n設計するdesign.jsonのフォーマットは、Pydanticスキーマとして定義されたSkillDesignクラスに従ってください。")
            
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_tmpl = f.read()

    # プロンプトの整形 (existing_name のみ引き渡し、コードは除外)
    existing_name_str = existing_name or "なし"
    formatted_prompt = prompt_tmpl.format(
        existing_name=existing_name_str,
        requirement=requirement
    )

    # Gemini API 用のマルチパーツ contents リスト構築
    contents = [formatted_prompt]
    
    if source_code:
        # ソースコードを独立したテキストパーツとしてシンプルに添付
        contents.append(source_code)

    # Gemini API の呼び出し
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が環境変数に設定されていません。")
    
    client = genai.Client(api_key=api_key)
    
    schema_dict = SkillDesign.model_json_schema()
    clean_schema = remove_additional_properties(schema_dict)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=clean_schema,
            temperature=0.1
        )
    )

    # レスポンスのパースとdesign.json of 保存
    design_data = json.loads(response.text)


    assets_output_dir = os.path.join(output_dir, "assets")
    output_file_path = os.path.join(assets_output_dir, "design.json")
    
    if not os.path.exists(assets_output_dir):
        os.makedirs(assets_output_dir)

    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(design_data, f, indent=2, ensure_ascii=False)

    tool_context.state["status"] = "success"
    tool_context.state["message"] = f"design.json が '{output_file_path}' に正常に生成されました。"
    tool_context.state["output_file_path"] = output_file_path
