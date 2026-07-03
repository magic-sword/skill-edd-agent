"""
SkillCommandLineRunner ＆ 共有セッション状態に準拠した、
skill-developer (スキル自動開発ワークフロー) のメイン起動スクリプト。
"""
import argparse
import asyncio
import os
import sys
import json
import uuid
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types
from google.adk.tools import ToolContext
from edd_agent_tools.testing.cli import SkillCommandLineRunner

# 動的解決用パス設定
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from workflow import root_workflow

async def run_developer_workflow(skill_name: str, prompt: str, tool_context: ToolContext = None):
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    session_id = str(uuid.uuid4())
    
    # 初期セッション状態
    initial_state = {
        "skill_name": skill_name,
        "prompt": prompt,
        "registry_path": "/workspace/src/skills_registry.json",
        "status": "running",
        "message": "Skill development workflow is running."
    }
    
    # 既存の tool_context 状態を引き継ぐ
    if tool_context:
        initial_state.update(tool_context.state.to_dict())

    # 起動前にセッションを作成
    await session_service.create_session(
        user_id="workflow_user",
        session_id=session_id,
        app_name="skill_developer_runner",
        state=initial_state
    )
    
    status = "success"
    message = "Workflow successfully completed."
    
    async with Runner(
        app_name="skill_developer_runner",
        agent=root_workflow,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        user_message = types.Content(
            role='user',
            parts=[types.Part(text="スキル開発ワークフローを開始してください。")]
        )
        
        try:
            async for event in runner.run_async(
                user_id="workflow_user",
                session_id=session_id,
                new_message=user_message,
            ):
                author = event.author or "Agent"
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(f"[{author}]: {part.text}")
                        if part.function_call:
                            print(f"[{author} ツール呼び出し]: {part.function_call.name}({part.function_call.args})")
                            
            # 完了後、セッション状態から最終結果を取得
            final_session = await session_service.get_session(user_id="workflow_user", session_id=session_id)
            if final_session and "status" in final_session.state:
                status = final_session.state["status"]
                message = final_session.state.get("message", message)
                if tool_context:
                    tool_context.state.update(final_session.state)
        except Exception as e:
            status = "failed"
            message = str(e)
            if tool_context:
                tool_context.state["status"] = "failed"
                tool_context.state["message"] = str(e)
            raise e
            
    if status == "failed":
        raise RuntimeError(f"Workflow failed: {message}")
        
    return f"Success: {message}"

def develop_skill_logic(tool_context: ToolContext):
    """
    SkillCommandLineRunner およびインプロセスツールから呼び出されるビジネスロジック。
    """
    skill_name = tool_context.state.get("skill_name")
    prompt = tool_context.state.get("prompt")
    
    if not skill_name or not prompt:
        raise ValueError("Error: 'skill_name' and 'prompt' are required.")
        
    # 非同期実行
    result = asyncio.run(run_developer_workflow(skill_name, prompt, tool_context))
    
    tool_context.state.update({
        "status": "success",
        "message": result
    })
