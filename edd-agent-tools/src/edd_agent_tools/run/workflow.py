"""
ワークフロー型モジュールの実行ライフサイクルをカプセル化するモジュール。
"""
from typing import Any

class WorkflowRunner:
    """
    ワークフロー型モジュールに共通する ADK Runner の起動、セッション管理、
    および状態同期の実行ライフサイクルをカプセル化するクラス。
    """
    def __init__(
        self,
        workflow_name: str,
        root_workflow: Any,
        tool_context: Any = None,
        session_service: Any = None,
        artifact_service: Any = None
    ):
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService

        self.workflow_name = workflow_name
        self.root_workflow = root_workflow
        self.tool_context = tool_context
        self.session_service = session_service or InMemorySessionService()
        self.artifact_service = artifact_service or InMemoryArtifactService()

    async def run_async(self, params: Any) -> dict[str, Any]:
        """非同期のワークフロー実行処理実体。"""
        import uuid
        from google.adk.runners import Runner
        from google.genai import types

        session_id = str(uuid.uuid4())
        
        # 初期状態の設定
        initial_state = {
            "status": "running",
            "message": f"Workflow {self.workflow_name} is running."
        }
        if self.tool_context:
            initial_state.update(self.tool_context.state.to_dict())
        initial_state.update(params.model_dump(exclude_unset=True))

        await self.session_service.create_session(
            user_id="workflow_user",
            session_id=session_id,
            app_name=f"{self.workflow_name}_runner",
            state=initial_state
        )
        
        status = "success"
        message = "Workflow successfully completed."
        output_dir = getattr(params, "output_dir", "") or ""
        
        async with Runner(
            app_name=f"{self.workflow_name}_runner",
            agent=self.root_workflow,
            session_service=self.session_service,
            artifact_service=self.artifact_service,
            auto_create_session=True
        ) as runner:
            user_message = types.Content(
                role='user',
                parts=[types.Part(text="ワークフローを開始してください。")]
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
                final_session = await self.session_service.get_session(
                    user_id="workflow_user",
                    session_id=session_id,
                    app_name=f"{self.workflow_name}_runner"
                )
                if final_session and "status" in final_session.state:
                    status = final_session.state["status"]
                    message = final_session.state.get("message", message)
                    output_dir = final_session.state.get("output_dir", output_dir)
                    if self.tool_context:
                        self.tool_context.state.update(final_session.state)
            except Exception as e:
                status = "failed"
                message = str(e)
                if self.tool_context:
                    self.tool_context.state["status"] = "failed"
                    self.tool_context.state["message"] = str(e)
                    self.tool_context.state["output_dir"] = output_dir
                raise e
                
        if status == "failed":
            raise RuntimeError(f"Workflow failed: {message}")
            
        # セッション状態辞書をそのまま返却
        return final_session.state if final_session else {}

    def run(self, params: Any) -> dict[str, Any]:
        """同期実行用ラッパーメソッド。"""
        import asyncio
        return asyncio.run(self.run_async(params))
