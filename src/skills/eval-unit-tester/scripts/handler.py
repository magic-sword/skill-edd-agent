from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "eval-unit-tester",
    "description": "指定されたスキルに対して評価用の単体テストスイート（*.evalset.json）を自動生成します。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill: str = Field(..., description='テストケースを生成する対象のスキル名')

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
