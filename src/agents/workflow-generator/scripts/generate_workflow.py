"""
ADKのサブエージェントを動的に起動し、
指定された要件に基づくワークフロー（SKILL.md, scripts/workflow.py, scripts/main.py）のコード実装を行うスクリプト。
"""
import argparse
import asyncio
import json
import os
import sys
import uuid
from google.adk.runners import Runner
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools import ToolContext

# 同一ディレクトリのサブモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phases
import import_generator

async def run_workflow_developer_agent(
    output_dir: str, 
    workflow_name: str, 
    prompt: str, 
    model: str, 
    max_turns: int,
    tool_context: ToolContext = None
):
    # パス情報の解析
    output_dir = os.path.abspath(output_dir)
    workflow_module_name = workflow_name.replace("-", "_")
    runner_name = "main.py"
    
    # テンプレートおよびプロンプトアセットのディレクトリ特定
    generator_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(generator_dir, "..", "assets")
    
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
    handler_tmpl_path = os.path.join(assets_dir, "handler.py.template")
    logic_tmpl_path = os.path.join(assets_dir, "workflow_logic.py.template")
    
    if os.path.exists(skill_md_tmpl_path):
        with open(skill_md_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        content = tmpl_content.replace("{workflow_name}", workflow_name).replace("{workflow_description}", prompt).replace("{workflow_module_name}", workflow_module_name)
        with open(os.path.join(output_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(content)
            
    if os.path.exists(workflow_tmpl_path):
        with open(workflow_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        content = tmpl_content.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)
        with open(os.path.join(output_dir, "scripts", "workflow.py"), "w", encoding="utf-8") as f:
            f.write(content)

    if os.path.exists(handler_tmpl_path):
        with open(handler_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        content = tmpl_content.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)
        with open(os.path.join(output_dir, "scripts", "handler.py"), "w", encoding="utf-8") as f:
            f.write(content)
            
    if os.path.exists(logic_tmpl_path):
        with open(logic_tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
        content = tmpl_content.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)
        with open(os.path.join(output_dir, "scripts", "workflow_logic.py"), "w", encoding="utf-8") as f:
            f.write(content)
    
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    
    # ----------------------------------------------------
    # フェーズ 1: 要件分解 (RequirementsAgent)
    # ----------------------------------------------------
    await phases.execute_phase1(
        output_dir=output_dir,
        workflow_name=workflow_name,
        prompt=prompt,
        model=model,
        session_id=session_id,
        session_service=session_service,
        artifact_service=artifact_service
    )
    
    # ----------------------------------------------------
    # フェーズ 2: 既存スキルマッピング (SkillMapperAgent)
    # ----------------------------------------------------
    await phases.execute_phase2(
        output_dir=output_dir,
        workflow_name=workflow_name,
        model=model,
        session_id=session_id,
        session_service=session_service,
        artifact_service=artifact_service
    )
    
    # ----------------------------------------------------
    # フェーズ 3: 難易度評価と安全中断判定 (ComplexityEvaluatorAgent)
    # ----------------------------------------------------
    await phases.execute_phase3(
        output_dir=output_dir,
        workflow_name=workflow_name,
        model=model,
        session_id=session_id,
        session_service=session_service,
        artifact_service=artifact_service
    )
    
    # 安全中断 (HALT) の決定論的判定
    halt_warning_path = os.path.join(output_dir, "assets", "halt_warning.md")
    if os.path.exists(halt_warning_path):
        print("\n" + "="*50)
        print("[HALT WARNING]: 新しいスキルまたはワークフローの開発が必要です。生成プロセスを中断します。")
        with open(halt_warning_path, "r", encoding="utf-8") as f:
            warning_text = f.read()
        print(warning_text)
        print("="*50 + "\n")
        if tool_context:
            tool_context.state["halt_warning_text"] = warning_text
        return

    # ----------------------------------------------------
    # フェーズ 4: 構造設計 (WorkflowDesignerAgent)
    # ----------------------------------------------------
    await phases.execute_phase4(
        output_dir=output_dir,
        workflow_name=workflow_name,
        model=model,
        session_id=session_id,
        session_service=session_service,
        artifact_service=artifact_service
    )
    
    # ----------------------------------------------------
    # 中間処理: インポート文の自動挿入 (import_generator.py)
    # ----------------------------------------------------
    print("[System]: 中間処理 (ツールロードコードの自動挿入) を実行します。")
    import_generator.insert_tool_imports(output_dir)
    
    # ----------------------------------------------------
    # フェーズ 5: 実装とドキュメント生成
    # ----------------------------------------------------
    await phases.execute_phase5(
        output_dir=output_dir,
        workflow_name=workflow_name,
        model=model,
        session_id=session_id,
        session_service=session_service,
        artifact_service=artifact_service
    )

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
        max_turns=max_turns,
        tool_context=tool_context
    )
    
    # 安全中断の検出
    if "halt_warning_text" in tool_context.state:
        warning_text = tool_context.state["halt_warning_text"]
        output_json_path = f"/workspace/src/.workflow_tmp/{workflow_name}/02_gen_out.json"
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "status": "halted",
                "message": "Generation halted due to missing prerequisite skills.",
                "warning": warning_text
            }, f, indent=2, ensure_ascii=False)
        return f"Halted: {warning_text}"
        
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
