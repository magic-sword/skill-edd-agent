from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "mock-executor",
    "description": "モック実行（シミュレーション）評価を実行するための専用のテスト実行スキル。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill: str = Field(..., description='評価対象スキルの名前またはパス')
    eval_set_path: str | None = Field(None, description='テストデータセットファイルのパス')
    config_file_path: str | None = Field(None, description='評価設定ファイルのパス')
    timeout_seconds: int | None = Field(None, description='評価のタイムアウト秒数')
    threshold_accuracy: float = Field(1.0, description='合格に必要な精度の閾値（0.0 から 1.0 の浮動小数点）。デフォルトは 1.0。')

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
