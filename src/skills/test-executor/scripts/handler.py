from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import process_message as run_logic


SKILL_METADATA = {
    "name": "test-executor",
    "description": "指定されたスキルのADK evalテストセットを安全なサブプロセス環境で実行し、ログから算出した精度が合格閾値以上か合否判定します。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill: str = Field(..., description='テスト対象のスキル名。')
    eval_set_path: str | None = Field(None, description='テストケースファイル（*.evalset.json）の絶対パス、または src ディレクトリからの相対パス。')
    threshold_accuracy: float = Field(1.0, description='合格に必要な精度の閾値（0.0 から 1.0 の浮動小数点）。デフォルトは 1.0 (100%合格)。')
    timeout_seconds: int = Field(180, description='テスト実行のタイムアウト制限（秒）。デフォルトは 180 秒。')

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
