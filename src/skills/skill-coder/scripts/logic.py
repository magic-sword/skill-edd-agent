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
from .models import Input
from .writer import PydanticModelWriter, HandlerWriter

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
            
    # 2. design.json のロード
    design_data: SkillDesign = directory.load_design()
    
    # 3. models.py & handler.py の決定論的自動生成
    coder_directory = registry.get_skill_directory(name="skill-coder")
    
    # 3-1. models.py の自動生成
    models_tmpl = coder_directory.load_asset("models.py.template")
    models_code = PydanticModelWriter(design_data, models_tmpl).write()
    models_path = os.path.join(scripts_dir, "models.py")
    with open(models_path, "w", encoding="utf-8") as f:
        f.write(models_code)
    print(f"決定論的モデルファイルを生成しました: {models_path}")
    
    # 3-2. handler.py の自動生成
    handler_tmpl = coder_directory.load_asset("handler.py.template")
    handler_code = HandlerWriter(design_data, handler_tmpl).write()
    handler_path = os.path.join(scripts_dir, "handler.py")
    with open(handler_path, "w", encoding="utf-8") as f:
        f.write(handler_code)
    print(f"決定論的ハンドラーファイルを生成しました: {handler_path}")
    
    # 3-3. __init__.py の決定論的自動生成 (テンプレートのコピー)
    init_tmpl = coder_directory.load_asset("__init__.py.template")
    init_path = os.path.join(scripts_dir, "__init__.py")
    with open(init_path, "w", encoding="utf-8") as f:
        f.write(init_tmpl)
    print(f"決定論的パッケージ初期化ファイルを生成しました: {init_path}")
    
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
        
        # 1回目およびエラー修復リトライのループ
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
        
        current_message = types.Content(
            role='user',
            parts=[types.Part(text=p) for p in builder.build()]
        )

        async with Runner(
            app_name="skill_coder_runner",
            agent=developer_agent,
            session_service=session_service,
            artifact_service=artifact_service,
            auto_create_session=True
        ) as runner:
            max_fix_attempts = 3
            for attempt in range(max_fix_attempts + 1):
                async for event in runner.run_async(
                    user_id="skill_coder",
                    session_id=session_id,
                    new_message=current_message,
                ):
                    author = event.author or "Agent"
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                print(f"[{author}]: {part.text}")
                            if part.function_call:
                                fc = part.function_call
                                print(f"[{author} ツール実行]: {fc.name}({fc.args})")

                # コンパイルチェックを実行して生成コードのインポート/構文を検証
                py_files = []
                for r, _, fs in os.walk(scripts_dir):
                    for f in fs:
                        if f.endswith(".py"):
                            py_files.append(os.path.join(r, f))
                
                if not py_files:
                    break

                import subprocess
                # py_compile で一括静的チェック
                check_res = subprocess.run(
                    ["python3", "-m", "py_compile"] + py_files,
                    capture_output=True, text=True
                )
                
                if check_res.returncode == 0:
                    print("✅ 生成されたすべての Python ファイルのコンパイルチェックに合格しました。")
                    break
                else:
                    if attempt == max_fix_attempts:
                        print(f"❌ 警告: {max_fix_attempts} 回の自己修復試行後もコンパイルエラーが解消されませんでした。")
                        break
                    
                    print(f"⚠️ コンパイルエラーを検出しました (自己修復試行 {attempt + 1}/{max_fix_attempts}):")
                    print(check_res.stderr)
                    
                    # エラーをフィードバックして再コーディングを要請
                    feedback_prompt = (
                        f"【警告: 生成されたコードにコンパイル/インポートエラーが発生しています】\n"
                        f"以下のエラー内容を確認し、該当ファイルのインポート文やクラス定義・メソッド名を正しく修正してください。\n"
                        f"※特に `google.generativeai` ではなく `google.genai` を使用しているか、"
                        f"また `edd_agent_tools.models` ではなく適切なモジュール（例: `edd_agent_tools.directory` 等）からインポートしているかを注意深く確認してください。\n\n"
                        f"エラー内容:\n{check_res.stderr}"
                    )
                    current_message = types.Content(
                        role='user',
                        parts=[types.Part(text=feedback_prompt)]
                    )

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