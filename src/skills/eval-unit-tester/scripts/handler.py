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
    skill_name: str = Field(..., description='テストケースを生成する対象のスキル名')

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # Stateパラメータを移行
    if params:
        for key, value in params.model_dump().items():
            if value is not None:
                tool_context.state[key] = value
            
    # ビジネスロジックを呼び出す
    run_logic(tool_context)
