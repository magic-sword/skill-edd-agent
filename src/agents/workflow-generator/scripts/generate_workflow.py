"""
ADKのサブエージェント（WorkflowDeveloperAgent）を動的に起動し、
指定された要件に基づくワークフロー（SKILL.md, scripts/workflow.py, scripts/run_****.py）のコード実装を行うスクリプト。
"""
import argparse
import asyncio
import json
import os
import sys
import uuid
from google.adk import Agent, Workflow
from google.adk.environment import LocalEnvironment
from google.adk.tools.environment import EnvironmentToolset
from google.adk.runners import Runner
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from google.adk.tools import ToolContext
from google.adk.tools.environment._read_file_tool import ReadFileTool
from google.adk.tools.environment._edit_file_tool import EditFileTool
from google.adk.tools.environment._write_file_tool import WriteFileTool
from edd_agent_tools.docs import LibraryDocumentationReader


async def run_workflow_developer_agent(output_dir: str, workflow_name: str, prompt: str, model: str, max_turns: int):
    # パス情報の解析
    output_dir = os.path.abspath(output_dir)
    workflow_module_name = workflow_name.replace("-", "_")
    runner_name = "main.py"
    
    # テンプレートおよびプロンプトアセットの読み込み
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(generator_dir, "..", "assets")
    
    # 指示アセットの読み込み
    def load_instruction(filename: str):
        path = os.path.join(assets_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Error: Instruction file {path} not found.")
        with open(path, "r", encoding="utf-8") as f:
            template = f.read()
        return template.replace(
            "{workflow_name}", workflow_name
        ).replace(
            "{output_dir}", output_dir
        ).replace(
            "{runner_name}", runner_name
        ).replace(
            "{workflow_module_name}", workflow_module_name
        )

    designer_inst = load_instruction("designer_instruction.txt")
    loader_inst = load_instruction("loader_instruction.txt")
    dag_inst = load_instruction("dag_instruction.txt")
    runner_inst = load_instruction("main_instruction.txt")
    doc_inst = load_instruction("doc_instruction.txt")
    
    # 共通ライブラリのドキュメントリーダー
    reader = LibraryDocumentationReader(library_name="edd_agent_tools")
    local_env = LocalEnvironment(working_dir=output_dir)
    
    # 5つのエージェントの定義
    designer_agent = Agent(
        model=model,
        name='WorkflowDesignerAgent',
        instruction=designer_inst,
        tools=[
            ReadFileTool(local_env),
            EditFileTool(local_env),
            WriteFileTool(local_env),
            reader.read_documentation,
        ]
    )
    
    loader_agent = Agent(
        model=model,
        name='ToolLoaderAgent',
        instruction=loader_inst,
        tools=[
            ReadFileTool(local_env),
            EditFileTool(local_env),
            WriteFileTool(local_env),
            reader.read_documentation,
        ]
    )
    
    dag_builder_agent = Agent(
        model=model,
        name='DagBuilderAgent',
        instruction=dag_inst,
        tools=[
            ReadFileTool(local_env),
            EditFileTool(local_env),
            WriteFileTool(local_env),
            reader.read_documentation,
        ]
    )
    
    main_generator_agent = Agent(
        model=model,
        name='MainGeneratorAgent',
        instruction=runner_inst,
        tools=[
            ReadFileTool(local_env),
            EditFileTool(local_env),
            WriteFileTool(local_env),
            reader.read_documentation,
        ]
    )
    
    doc_generator_agent = Agent(
        model=model,
        name='DocGeneratorAgent',
        instruction=doc_inst,
        tools=[
            ReadFileTool(local_env),
            EditFileTool(local_env),
            WriteFileTool(local_env),
            reader.read_documentation,
        ]
    )
    
    # ワークフローの開発DAG接続
    workflow_dev_workflow = Workflow(
        name="workflow_developer_workflow",
        edges=[
            ("START", designer_agent),
            (designer_agent, loader_agent),
            (loader_agent, dag_builder_agent),
            (dag_builder_agent, main_generator_agent),
            (main_generator_agent, doc_generator_agent)
        ]
    )
    
    session_id = str(uuid.uuid4())
    print(f"ワークフロー開発マルチエージェントを起動中... (セッションID: {session_id})")
    
    # ディレクトリの作成保証
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "references"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "assets"), exist_ok=True)

    # テンプレートファイルをコピー・展開
    skill_md_tmpl_path = os.path.join(assets_dir, "SKILL.md.template")
    workflow_tmpl_path = os.path.join(assets_dir, "workflow.py.template")
    runner_tmpl_path = os.path.join(assets_dir, "main.py.template")
    
    if os.path.exists(skill_md_tmpl_path):
        with open(skill_md_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        content = tmpl_content.replace("{workflow_name}", workflow_name).replace("{workflow_description}", prompt).replace("{workflow_module_name}", workflow_module_name)
        with open(os.path.join(output_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(content)
            
    if os.path.exists(workflow_tmpl_path):
        with open(workflow_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        content = tmpl_content.replace("{workflow_name}", workflow_name)
        with open(os.path.join(output_dir, "scripts", "workflow.py"), "w", encoding="utf-8") as f:
            f.write(content)

    if os.path.exists(runner_tmpl_path):
        with open(runner_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        content = tmpl_content.replace("{workflow_name}", workflow_name)
        with open(os.path.join(output_dir, "scripts", runner_name), "w", encoding="utf-8") as f:
            f.write(content)
    
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    
    async with Runner(
        app_name="workflow_generator_runner",
        agent=workflow_dev_workflow,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        user_message = types.Content(
            role='user',
            parts=[types.Part(text=f"以下の要件に従って、対象ワークフローのDAG定義および起動スクリプトを実装してください：\n{prompt}")]
        )
        
        async for event in runner.run_async(
            user_id="workflow_generator",
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

async def generate_workflow_code(tool_context: ToolContext) -> str:
    """
    指定された要件（prompt）に基づき、WorkflowDeveloperAgent を起動して
    新規ワークフローエージェントを自律生成します。
    """
    workflow_name = tool_context.state.get("workflow_name")
    prompt = tool_context.state.get("prompt")
    output_dir = tool_context.state.get("output_dir")
    
    if not workflow_name or not prompt:
        raise ValueError("セッション状態に 'workflow_name' または 'prompt' が設定されていません。")
        
    if not output_dir:
        output_dir = os.path.abspath(f"/workspace/src/agents/{workflow_name}")
    else:
        output_dir = os.path.abspath(output_dir)
        
    model = "gemini-2.5-flash"
    max_turns = 15
    
    # 開発者エージェントを実行
    await run_workflow_developer_agent(
        output_dir=output_dir,
        workflow_name=workflow_name,
        prompt=prompt,
        model=model,
        max_turns=max_turns
    )
    
    # スキル仕様書（SKILL.md）が作成されたことを確認
    skill_md_path = os.path.join(output_dir, "SKILL.md")
    if not os.path.exists(skill_md_path):
        raise ValueError(f"Workflow specification 'SKILL.md' was not generated at {skill_md_path}.")
        
    output_json_path = f"/workspace/src/.workflow_tmp/{workflow_name}/02_gen_out.json"
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "success",
            "message": "Successfully generated workflow.",
            "output_dir": output_dir
        }, f, indent=2, ensure_ascii=False)
        
    tool_context.state["workflow_dir"] = output_dir
    
    return f"Success: Generated workflow '{workflow_name}' at '{output_dir}'."

