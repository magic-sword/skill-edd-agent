from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .eval_unit_tester import execute_unit_tester_logic as run_tester_logic

SKILL_METADATA = {
    "name": "eval-unit-tester",
    "description": "指定されたスキルに対して評価用の単体テストスイート（*.evalset.json）を自動生成します。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill_name: str = Field(..., description="テストケースを生成する対象のスキル名")

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # ロジックが期待するStateを設定
    tool_context.state["skill_name"] = params.skill_name
    
    # 既存のビジネスロジックを実行
    run_tester_logic(tool_context)
