import asyncio
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .generate_workflow import generate_workflow_code as run_generator_logic

SKILL_METADATA = {
    "name": "workflow-generator",
    "description": "要件（prompt）に基づいてGoogle ADK 2.0互換の新しいワークフローエージェントを自律生成・構成します。",
    "execution_type": "workflow",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    workflow_name: str = Field(..., description="生成するワークフローエージェントの名前 (例: data-pipeline)")
    prompt: str = Field(..., description="ワークフローの要件や手順")
    output_dir: str | None = Field(None, description="出力先ディレクトリのパス")

def process_message(params: Input, tool_context: ToolContext) -> str:
    # 非同期ロジックを実行
    return asyncio.run(run_generator_logic(params, tool_context))
