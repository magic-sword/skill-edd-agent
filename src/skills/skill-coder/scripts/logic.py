import os
import json
import uuid
import asyncio
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from google.adk import Agent
from google.adk.environment import LocalEnvironment
from google.adk.tools.environment._read_file_tool import ReadFileTool
from google.adk.tools.environment._edit_file_tool import EditFileTool
from google.adk.tools.environment._write_file_tool import WriteFileTool
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types
from edd_agent_tools.registry import SkillRegistry
from edd_agent_tools.models import SkillDesign
from edd_agent_tools.docs import LibraryDocumentationReader
from .handler import Input

def generate_handler_code(design: SkillDesign, template_str: str) -> str:
    """
    SkillDesignメタデータから、Pydantic Inputクラス定義と薄いルーティング処理を含む
    scripts/handler.py のソースコードを決定論的に自動生成します。
    """
    fields = []
    has_any = False
    
    for param in design.parameters:
        t_str = param.type.strip().lower()
        if t_str == "str":
            python_type = "str"
        elif t_str == "int":
            python_type = "int"
        elif t_str == "bool":
            python_type = "bool"
        elif t_str == "float":
            python_type = "float"
        elif t_str == "list":
            python_type = "list"
        else:
            python_type = "Any"
            has_any = True
            
        if param.required:
            default_expr = "..."
            annotated_type = python_type
        else:
            if param.default is None:
                default_expr = "None"
                annotated_type = f"{python_type} | None"
            else:
                annotated_type = python_type
                if t_str == "str":
                    default_expr = repr(param.default)
                elif t_str == "bool":
                    default_expr = "True" if str(param.default).lower() in ("true", "1", "yes") else "False"
                elif t_str in ("int", "float"):
                    default_expr = str(param.default)
                else:
                    default_expr = repr(param.default)
                    
        field_str = f"    {param.name}: {annotated_type} = Field({default_expr}, description={repr(param.description)})"
        fields.append(field_str)
        
    fields_str = "\n".join(fields) if fields else "    pass"
    
    metadata = {
        "name": design.name,
        "description": design.description,
        "execution_type": design.execution_type,
        "output_mode": design.output_mode,
        "dependencies": design.dependencies
    }
    metadata_str = json.dumps(metadata, indent=4, ensure_ascii=False)
    
    any_import = "from typing import Any\n" if has_any else ""
    
    return template_str.format(
        any_import=any_import,
        metadata_str=metadata_str,
        fields_str=fields_str
    )

def process_message(params: Input, tool_context: ToolContext) -> str:
    """
    skill-coder のメインビジネスロジック。
    - design.json をロードし、scripts/handler.py を決定論的に自動生成。
    - SkillDeveloperAgent を起動して、オブジェクト指向で分割されたビジネスロジックコード（logic.py等）を段階的にコーディング。
    """
    prompt = params.prompt
    skill = params.skill
    design_path = params.design_path
    output_dir = params.output_dir
    
    if not prompt:
        raise ValueError("必須パラメータ 'prompt' が指定されていません。")
    if not skill and not design_path:
        raise ValueError("対象スキルを特定するために、'skill' または 'design_path' のいずれか一方は必ず指定する必要があります。")
        
    registry = SkillRegistry()
    
    design_path_fallback = os.path.abspath(design_path) if design_path else None
    directory = registry.get_skill_directory(name=skill, design_path=design_path_fallback)
    
    skill_name = directory.name
    target_root = os.path.abspath(output_dir or directory.root_dir)
    scripts_dir = os.path.join(target_root, "scripts")
    
    # 1. 必要なディレクトリ構成の確保
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(os.path.join(target_root, "assets"), exist_ok=True)
    os.makedirs(os.path.join(target_root, "references"), exist_ok=True)
    
    # scripts/__init__.py の配置
    init_py_path = os.path.join(scripts_dir, "__init__.py")
    if not os.path.exists(init_py_path):
        with open(init_py_path, "w", encoding="utf-8") as f:
            f.write("#\n")
            
    # 2. design.json のロード
    design_data: SkillDesign = directory.load_design()
    
    # 3. handler.py の決定論的自動生成
    coder_directory = registry.get_skill_directory(name="skill-coder")
    handler_tmpl = coder_directory.load_asset("handler.py.template")
    handler_code = generate_handler_code(design_data, handler_tmpl)
    handler_path = os.path.join(scripts_dir, "handler.py")
    with open(handler_path, "w", encoding="utf-8") as f:
        f.write(handler_code)
    print(f"決定論的ハンドラーファイルを生成しました: {handler_path}")
    
    # 4. logic.py のプレースホルダー配置（存在しない場合のみ）
    logic_path = os.path.join(scripts_dir, "logic.py")
    if not os.path.exists(logic_path):
        logic_tmpl = coder_directory.load_asset("logic.py.template")
        with open(logic_path, "w", encoding="utf-8") as f:
            f.write(logic_tmpl)
            
    # 5. システムプロンプト (system_instruction.txt) のロードとプレースホルダー置換
    system_instruction_tmpl = coder_directory.load_asset("system_instruction.txt")
    
    instruction = system_instruction_tmpl.replace(
        "{skill_name}", skill_name
    ).replace(
        "{output_dir}", target_root
    ).replace(
        "{design_json}", json.dumps(design_data.model_dump(), indent=2, ensure_ascii=False)
    ).replace(
        "{prompt}", prompt
    )
    
    # 6. SkillDeveloperAgent の起動とコーディング実行
    async def run_developer_agent():
        local_env = LocalEnvironment(working_dir=target_root)
        reader = LibraryDocumentationReader(library_name="edd_agent_tools")
        
        developer_agent = Agent(
            model="gemini-2.5-flash",
            name='SkillDeveloperAgent',
            instruction=instruction,
            tools=[
                ReadFileTool(local_env),
                EditFileTool(local_env),
                WriteFileTool(local_env),
                reader.read_documentation
            ]
        )
        
        session_service = InMemorySessionService()
        artifact_service = InMemoryArtifactService()
        session_id = str(uuid.uuid4())
        
        async with Runner(
            app_name="skill_coder_runner",
            agent=developer_agent,
            session_service=session_service,
            artifact_service=artifact_service,
            auto_create_session=True
        ) as runner:
            user_prompt_tmpl = coder_directory.load_asset("user_prompt.txt")
            user_prompt = user_prompt_tmpl.format(
                skill_name=skill_name,
                prompt=prompt
            )
            
            # GeminiContentBuilder を使って、指示と既存ソースコード、規約をマルチパーツ化
            from edd_agent_tools.gemini import GeminiContentBuilder
            builder = GeminiContentBuilder(user_prompt)
            
            # 既存の scripts ディレクトリ内の全 python ファイル (handler.py 含む) を添付
            if os.path.exists(scripts_dir):
                builder.add_dir(
                    directory=scripts_dir,
                    ref_root=target_root,
                    file_filter=lambda p: p.endswith(".py")
                )
                
            docs_content = reader.read_documentation()
            builder.parts.append(f"=== 開発規約（edd-agent-tools 仕様書） ===\n{docs_content}")
            
            user_message = types.Content(
                role='user',
                parts=[types.Part(text=p) for p in builder.build()]
            )
            
            async for event in runner.run_async(
                user_id="skill_coder",
                session_id=session_id,
                new_message=user_message,
            ):
                author = event.author or "Agent"
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(f"[{author}]: {part.text}")
                        if part.function_call:
                            fc = part.function_call
                            print(f"[{author} ツール実行]: {fc.name}({fc.args})")

    # 同期処理として非同期エージェントを実行
    asyncio.run(run_developer_agent())
    
    # 生成されたファイルをスキャンして報告
    generated_files = []
    for root, _, files in os.walk(scripts_dir):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), target_root)
            generated_files.append(rel_path)
            
    assets_dir = os.path.join(target_root, "assets")
    if os.path.exists(assets_dir):
        for root, _, files in os.walk(assets_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), target_root)
                generated_files.append(rel_path)
                
    message = f"スキルコードの実装が完了しました。生成/更新ファイル: {', '.join(generated_files)}"
    tool_context.state["status"] = "success"
    tool_context.state["generated_files"] = generated_files
    tool_context.state["result_message"] = message
    
    return message