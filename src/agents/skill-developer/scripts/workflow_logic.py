"""
skill-developer のメイン起動ビジネスロジック。
"""
import asyncio
import os
import sys
import uuid
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types
from google.adk.tools import ToolContext
from .models import Input, Output

# 同一ディレクトリのビジネスロジックモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from .workflow import root_workflow

async def run_workflow_instance(params: Input, tool_context: ToolContext = None) -> str:
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    session_id = str(uuid.uuid4())
    
    # 初期セッション状態を構築
    initial_state = {
        "status": "running",
        "message": "Workflow skill-developer is running.",
        "prompt": params.prompt, # skill-designer に渡すプロンプト
        "skill": params.skill,   # skill-designer に渡すスキル名
        "output_dir": params.output_dir # 各スキルに渡す出力ディレクトリ
    }
    
    # パラメータと既存の tool_context 状態を引き継ぐ
    if tool_context:
        initial_state.update(tool_context.state.to_dict())
    
    # 入力パラメータをセッション状態にセット（重複するが念のため）
    initial_state.update(params.model_dump())

    # 起動前にセッションを作成
    await session_service.create_session(
        user_id="workflow_user",
        session_id=session_id,
        app_name="skill-developer_runner",
        state=initial_state
    )
    
    status = "success"
    message = "Workflow successfully completed."
    output_dir_val = "" # 最終的なスキルディレクトリのパスを保持
    
    async with Runner(
        app_name="skill-developer_runner",
        agent=root_workflow,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True
    ) as runner:
        user_message = types.Content(
            role='user',
            parts=[types.Part(text=f"スキル開発ワークフローを開始してください。要件: {params.prompt}")]
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
                output_dir_val = final_session.state.get("output_dir", "") # 各スキル(またはspec-writer)の出力から取得
                
                if tool_context:
                    # tool_context の状態を更新
                    tool_context.state["status"] = status
                    tool_context.state["message"] = message
                    tool_context.state["output_dir"] = output_dir_val # 最終出力パスを保存

        except Exception as e:
            status = "failed"
            message = str(e)
            if tool_context:
                tool_context.state["status"] = "failed"
                tool_context.state["message"] = str(e)
                tool_context.state["output_dir"] = "" # 失敗時はパスはなし
            raise e
            
    if status == "failed":
        raise RuntimeError(f"Workflow failed: {message}")
        
    # Output モデルにマッピングして返す
    return Output(status=status, message=message, output_dir=output_dir_val).model_dump_json()

def workflow_logic(params: Input, tool_context: ToolContext) -> str:
    """
    インプロセスツールおよび共通CLIランナーから呼び出されるビジネスロジック。
    """
    result = asyncio.run(run_workflow_instance(params, tool_context))
    return result
