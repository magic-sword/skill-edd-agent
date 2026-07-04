from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .evaluate_trigger import execute_trigger_logic as run_trigger_logic

SKILL_METADATA = {
    "name": "trigger-evaluator",
    "description": "指定されたスキルのSKILL.md内のトリガー条件の静的評価、およびトリガー評価用テストケースの自動生成を行います。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill_name: str = Field(..., description="評価対象のスキル名")

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # ロジックが期待するStateを設定
    tool_context.state["skill_name"] = params.skill_name
    
    # 既存のビジネスロジックを実行
    run_trigger_logic(tool_context)
