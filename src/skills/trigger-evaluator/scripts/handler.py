from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "trigger-evaluator",
    "description": "指定されたスキルのSKILL.md内のトリガー条件の静的評価、およびトリガー評価用テストケースの自動生成を行います。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill: str = Field(..., description='評価対象のスキル名')

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
