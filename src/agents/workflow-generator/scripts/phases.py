import os
import sys
import pathlib
from google.adk import Agent, Workflow
from google.adk.environment import LocalEnvironment
from google.adk.tools.environment._read_file_tool import ReadFileTool
from google.adk.tools.environment._edit_file_tool import EditFileTool
from google.adk.tools.environment._write_file_tool import WriteFileTool
from google.adk.runners import Runner
from google.genai import types
from edd_agent_tools.docs import LibraryDocumentationReader
from edd_agent_tools.registry import SkillRegistry
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset

def build_skill_toolset(workflow_name: str) -> SkillToolset:
    """登録されているすべてのスキルをスキャンして SkillToolset を構築します。"""
    registry = SkillRegistry()
    skills_list = []
    try:
        skills = registry.list_skills()
        for skill in skills:
            if skill.name in ["workflow-generator", workflow_name]:
                continue
            skill_dir = skill.root_dir
            if skill_dir:
                try:
                    skill_obj = load_skill_from_dir(pathlib.Path(skill_dir))
                    skills_list.append(skill_obj)
                except Exception as e:
                    print(f"[System Warning]: スキル '{skill.name}' のロードに失敗しました: {e}")
    except Exception as e:
        print(f"[System Warning]: 登録スキルの取得中にエラーが発生しました: {e}")
        
    return SkillToolset(skills=skills_list)

async def execute_phase1(output_dir: str, workflow_name: str, prompt: str, model: str, session_id: str, session_service, artifact_service):
    """フェーズ1: 要件分解 (RequirementsAgent)"""
    print("[System]: フェーズ 1 (要件定義の自然言語分解) を開始します。")
    local_env = LocalEnvironment(working_dir=output_dir)
    reader = LibraryDocumentationReader(library_name="edd_agent_tools")
    
    # アセットの読み込みヘルパー
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(generator_dir, "..", "assets")
    with open(os.path.join(assets_dir, "requirements_instruction.txt"), "r", encoding="utf-8") as f:
        inst = f.read().replace("{workflow_name}", workflow_name).replace("{output_dir}", output_dir)
        
    requirements_agent = Agent(
        model=model,
        name='RequirementsAgent',
        instruction=inst,
        tools=[ReadFileTool(local_env), EditFileTool(local_env), WriteFileTool(local_env), reader.read_documentation]
    )
    
    wf = Workflow(name="phase1_requirements", edges=[("START", requirements_agent)])
    
    async with Runner(
        app_name="workflow_generator_runner",
        agent=wf,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        msg = types.Content(
            role='user',
            parts=[types.Part(text=f"以下の要件に従って、タスクの実行手順を自然言語で整理し、assets/requirements.md に出力してください：\n{prompt}")]
        )
        async for event in runner.run_async(user_id="workflow_generator", session_id=session_id, new_message=msg):
            author = event.author or "Agent"
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{author}]: {part.text}")
                    if part.function_call:
                        print(f"[{author} ツール実行]: {part.function_call.name}({part.function_call.args})")

async def execute_phase2(output_dir: str, workflow_name: str, model: str, session_id: str, session_service, artifact_service):
    """フェーズ2: 既存スキルのマッピング (SkillMapperAgent)"""
    print("[System]: フェーズ 2 (既存スキルのマッピング) を開始します。")
    local_env = LocalEnvironment(working_dir=output_dir)
    reader = LibraryDocumentationReader(library_name="edd_agent_tools")
    skill_toolset = build_skill_toolset(workflow_name)
    
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(generator_dir, "..", "assets")
    with open(os.path.join(assets_dir, "mapper_instruction.txt"), "r", encoding="utf-8") as f:
        inst = f.read().replace("{workflow_name}", workflow_name).replace("{output_dir}", output_dir)
        
    mapper_agent = Agent(
        model=model,
        name='SkillMapperAgent',
        instruction=inst,
        tools=[ReadFileTool(local_env), EditFileTool(local_env), WriteFileTool(local_env), reader.read_documentation, skill_toolset]
    )
    
    wf = Workflow(name="phase2_mapping", edges=[("START", mapper_agent)])
    
    async with Runner(
        app_name="workflow_generator_runner",
        agent=wf,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        msg = types.Content(
            role='user',
            parts=[types.Part(text="assets/requirements.md の各タスクについて、SkillToolset を活用して既存のスキルとマッピングし、assets/mapping.json を出力してください。")]
        )
        async for event in runner.run_async(user_id="workflow_generator", session_id=session_id, new_message=msg):
            author = event.author or "Agent"
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{author}]: {part.text}")
                    if part.function_call:
                        print(f"[{author} ツール実行]: {part.function_call.name}({part.function_call.args})")

async def execute_phase3(output_dir: str, workflow_name: str, model: str, session_id: str, session_service, artifact_service):
    """フェーズ3: 難易度評価と安全中断判定 (ComplexityEvaluatorAgent)"""
    print("[System]: フェーズ 3 (不足タスクの難易度評価) を開始します。")
    local_env = LocalEnvironment(working_dir=output_dir)
    reader = LibraryDocumentationReader(library_name="edd_agent_tools")
    
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(generator_dir, "..", "assets")
    with open(os.path.join(assets_dir, "evaluator_instruction.txt"), "r", encoding="utf-8") as f:
        inst = f.read().replace("{workflow_name}", workflow_name).replace("{output_dir}", output_dir)
        
    evaluator_agent = Agent(
        model=model,
        name='ComplexityEvaluatorAgent',
        instruction=inst,
        tools=[ReadFileTool(local_env), EditFileTool(local_env), WriteFileTool(local_env), reader.read_documentation]
    )
    
    wf = Workflow(name="phase3_evaluation", edges=[("START", evaluator_agent)])
    
    async with Runner(
        app_name="workflow_generator_runner",
        agent=wf,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        msg = types.Content(
            role='user',
            parts=[types.Part(text="assets/mapping.json を読み込み、不足タスクの難易度を評価してください。難易度2または3が含まれる場合は、assets/halt_warning.md に警告を出力してください。")]
        )
        async for event in runner.run_async(user_id="workflow_generator", session_id=session_id, new_message=msg):
            author = event.author or "Agent"
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{author}]: {part.text}")
                    if part.function_call:
                        print(f"[{author} ツール実行]: {part.function_call.name}({part.function_call.args})")

async def execute_phase4(output_dir: str, workflow_name: str, model: str, session_id: str, session_service, artifact_service):
    """フェーズ4: 構造設計 (WorkflowDesignerAgent)"""
    print("[System]: フェーズ 4 (構造設計) を開始します。")
    local_env = LocalEnvironment(working_dir=output_dir)
    reader = LibraryDocumentationReader(library_name="edd_agent_tools")
    skill_toolset = build_skill_toolset(workflow_name)
    
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(generator_dir, "..", "assets")
    with open(os.path.join(assets_dir, "designer_instruction.txt"), "r", encoding="utf-8") as f:
        inst = f.read().replace("{workflow_name}", workflow_name).replace("{output_dir}", output_dir)
        
    designer_agent = Agent(
        model=model,
        name='WorkflowDesignerAgent',
        instruction=inst,
        tools=[ReadFileTool(local_env), EditFileTool(local_env), WriteFileTool(local_env), reader.read_documentation, skill_toolset]
    )
    
    wf = Workflow(name="phase4_design", edges=[("START", designer_agent)])
    
    async with Runner(
        app_name="workflow_generator_runner",
        agent=wf,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        msg = types.Content(
            role='user',
            parts=[types.Part(text="assets/mapping.json の内容に基づき、対象ワークフローの設計書 (assets/design.json) を作成してください。")]
        )
        async for event in runner.run_async(user_id="workflow_generator", session_id=session_id, new_message=msg):
            author = event.author or "Agent"
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{author}]: {part.text}")
                    if part.function_call:
                        print(f"[{author} ツール実行]: {part.function_call.name}({part.function_call.args})")

async def execute_phase5(output_dir: str, workflow_name: str, model: str, session_id: str, session_service, artifact_service):
    """フェーズ5: コード実装とドキュメント生成 (ToolLoaderAgent, DagBuilderAgent, MainGeneratorAgent, DocGeneratorAgent)"""
    print("[System]: フェーズ 5 (実装・ドキュメント生成フェーズ) を開始します。")
    local_env = LocalEnvironment(working_dir=output_dir)
    reader = LibraryDocumentationReader(library_name="edd_agent_tools")
    skill_toolset = build_skill_toolset(workflow_name)
    
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(generator_dir, "..", "assets")
    
    # テンプレートからの指示ロード
    def load_instruction(filename: str):
        with open(os.path.join(assets_dir, filename), "r", encoding="utf-8") as f:
            template = f.read()
        return template.replace("{workflow_name}", workflow_name).replace("{output_dir}", output_dir).replace("{runner_name}", "handler.py").replace("{workflow_module_name}", workflow_name.replace("-", "_"))

    loader_inst = load_instruction("loader_instruction.txt")
    dag_inst = load_instruction("dag_instruction.txt")
    runner_inst = load_instruction("handler_instruction.txt")
    doc_inst = load_instruction("doc_instruction.txt")
    
    loader_agent = Agent(model=model, name='ToolLoaderAgent', instruction=loader_inst, tools=[ReadFileTool(local_env), EditFileTool(local_env), WriteFileTool(local_env), reader.read_documentation, skill_toolset])
    dag_builder_agent = Agent(model=model, name='DagBuilderAgent', instruction=dag_inst, tools=[ReadFileTool(local_env), EditFileTool(local_env), WriteFileTool(local_env), reader.read_documentation, skill_toolset])
    main_generator_agent = Agent(model=model, name='MainGeneratorAgent', instruction=runner_inst, tools=[ReadFileTool(local_env), EditFileTool(local_env), WriteFileTool(local_env), reader.read_documentation, skill_toolset])
    doc_generator_agent = Agent(model=model, name='DocGeneratorAgent', instruction=doc_inst, tools=[ReadFileTool(local_env), EditFileTool(local_env), WriteFileTool(local_env), reader.read_documentation, skill_toolset])
    
    wf = Workflow(
        name="phase5_implementation",
        edges=[
            ("START", loader_agent),
            (loader_agent, dag_builder_agent),
            (dag_builder_agent, main_generator_agent),
            (main_generator_agent, doc_generator_agent)
        ]
    )
    
    async with Runner(
        app_name="workflow_generator_runner",
        agent=wf,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        msg = types.Content(
            role='user',
            parts=[types.Part(text="設計書 assets/design.json が作成され、scripts/workflow.py に依存ツールのロード定義が自動的かつ正確に記述されました。この状態から残りの実装（各Agentの定義、DAGの接続、main.pyの引数調整、SKILL.mdの完成）を始めてください。")]
        )
        async for event in runner.run_async(user_id="workflow_generator", session_id=session_id, new_message=msg):
            author = event.author or "Agent"
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{author}]: {part.text}")
                    if part.function_call:
                        print(f"[{author} ツール実行]: {part.function_call.name}({part.function_call.args})")
