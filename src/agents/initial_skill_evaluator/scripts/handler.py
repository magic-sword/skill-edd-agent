from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .evaluator_workflow import workflow_logic as run_workflow_logic

SKILL_METADATA = {
    "name": "initial_skill_evaluator",
    "description": "新規スキルの初期評価（トリガー評価およびテスト実行）を一括で行うワークフロー。",
    "execution_type": "workflow",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill: str = Field(..., description="評価対象のスキル名")
    eval_set_path: str | None = Field(None, description="評価用テストセットファイルのパス")

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # ロジックが期待するStateを設定
    tool_context.state["skill"] = params.skill
    tool_context.state["eval_set_path"] = params.eval_set_path
    
    # 既存のビジネスロジックを実行
    run_workflow_logic(tool_context)
