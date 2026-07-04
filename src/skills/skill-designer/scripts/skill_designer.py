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
    name = tool_context.state.get("name")
    source_code_dir = tool_context.state.get("source_code_dir")

    from edd_agent_tools.registry import SkillRegistry
    registry = SkillRegistry()
    registry.load()

    # 1. 共通パス特定
    resolved = None
    if name:
        resolved = registry.resolve_skill_paths(name)
        if not output_dir:
            output_dir = resolved["component_root"]
        if not source_code_dir:
            source_code_dir = resolved["source_code_dir"]

    if not output_dir:
        raise ValueError("Error: 'output_dir' or 'name' must be provided.")

    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(os.path.join("/workspace", output_dir))

    # 2. 既存スキル名の特定
    existing_name = name
    if not existing_name:
        design_json_path = os.path.join(output_dir, "assets", "design.json")
        if os.path.exists(design_json_path):
            try:
                with open(design_json_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    if isinstance(old_data, dict) and old_data.get("name"):
                        existing_name = old_data["name"]
            except Exception:
                pass
        if not existing_name and os.path.basename(output_dir) not in ["", ".", ".."]:
            existing_name = os.path.basename(output_dir)

    # 3. 既存ソースコード（ディレクトリ全体または単一ファイル）の収集
    source_code = ""
    scan_target = source_code_dir

    if scan_target:
        if not os.path.isabs(scan_target):
            scan_target = os.path.abspath(os.path.join("/workspace", scan_target))
    elif output_dir:
        scan_target = os.path.join(output_dir, "scripts")

    if scan_target and os.path.exists(scan_target):
        if os.path.isdir(scan_target):
            py_files = []
            for root, dirs, files in os.walk(scan_target):
                for f in files:
                    if f.endswith(".py"):
                        py_files.append(os.path.join(root, f))
            if py_files:
                combined_code = []
                ref_root = output_dir if output_dir else os.path.dirname(scan_target)
                for file_path in sorted(py_files):
                    rel_path = os.path.relpath(file_path, ref_root)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        combined_code.append(f"# --- File: {rel_path} ---\n{content}")
                    except Exception as e:
                        print(f"Warning: Failed to read {file_path}: {e}")
                source_code = "\n\n".join(combined_code)
        else:
            try:
                with open(scan_target, "r", encoding="utf-8") as f:
                    source_code = f.read()
            except Exception as e:
                print(f"Warning: Failed to read {scan_target}: {e}")

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

    # プロンプトアセットのロード
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "..", "assets", "prompt.txt")
    
    assets_dir = os.path.join(script_dir, "..", "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    if not os.path.exists(prompt_path):
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write("あなたは優秀なスキルデザイナーです。以下の情報に基づき、ADK 2.0互換のdesign.jsonを設計してください。\n\n既存のスキル名:\n{existing_name}\n\n要件詳細:\n{requirement}\n\n既存の制約事項:\n{existing_constraints}")
            
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_tmpl = f.read()

    # プロンプトの整形
    existing_name_str = existing_name or "なし"
    formatted_prompt = prompt_tmpl.format(
        existing_name=existing_name_str,
        requirement=requirement,
        existing_constraints=existing_constraints_str
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
