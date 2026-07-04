import os
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
    name = tool_context.state.get("name")
    source_code_dir = tool_context.state.get("source_code_dir")

    from edd_agent_tools.registry import SkillRegistry
    registry = SkillRegistry()
    registry.load()

    # 1. スキルフォルダの解決
    design_path_fallback = None
    if not name and output_dir:
        design_path_fallback = os.path.join(os.path.abspath(output_dir), "assets", "design.json")

    directory = registry.get_skill_directory(name=name, design_path=design_path_fallback)
    existing_name = directory.name

    output_dir = os.path.abspath(output_dir or directory.root_dir)
    scan_target = os.path.abspath(source_code_dir or directory.source_code_dir)

    # 既存の制約事項を抽出
    existing_constraints_str = "なし"
    if existing_name:
        from edd_agent_tools.parser import PydanticModelParser
        try:
            handler_module = registry.load_handler(existing_name)
            InputSchema = getattr(handler_module, "Input", None)
            if InputSchema:
                extracted = PydanticModelParser.parse_constraints(InputSchema)
                if extracted:
                    existing_constraints_str = "\n".join(f"- {c}" for c in extracted)
        except Exception as e:
            print(f"Info: Could not load handler.py for validator constraint parsing in designer: {e}")

    # 3. プロンプトアセットのロード
    designer_dir = registry.get_skill_directory("skill-designer")
    prompt_tmpl = designer_dir.load_asset("prompt.txt")

    # プロンプトの整形
    existing_name_str = existing_name or "なし"
    formatted_prompt = prompt_tmpl.format(
        existing_name=existing_name_str,
        requirement=requirement,
        existing_constraints=existing_constraints_str
    )

    # Gemini API 用のマルチパーツ contents リスト構築
    from edd_agent_tools.gemini import GeminiContentBuilder
    builder = GeminiContentBuilder(formatted_prompt)
    if scan_target:
        ref_root = output_dir if output_dir else os.path.dirname(scan_target)
        builder.add_dir(scan_target, ref_root=ref_root, file_filter=lambda p: p.endswith(".py"))
        
    # プロジェクト共通規約（README.md）をコンテキストに添付
    from edd_agent_tools.docs import LibraryDocumentationReader
    try:
        reader = LibraryDocumentationReader(library_name="edd_agent_tools")
        docs_content = reader.read_documentation()
        builder.add_text_part(
            text=f"=== プロジェクト共通開発規約 ===\n{docs_content}",
            display_name="README.md"
        )
    except Exception as e:
        print(f"Info: Could not load README.md in designer: {e}")
        
    contents = builder.build()

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
