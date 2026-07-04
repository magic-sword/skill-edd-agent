from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .execute_test import execute_test_logic as run_test_logic

SKILL_METADATA = {
    "name": "test-executor",
    "description": "指定されたスキルのADK evalテストセットを実行し、合格閾値に基づいて合否判定を行います。デッドロック防止のタイムアウト機能を備えています。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill_name: str = Field(..., description="テスト対象のスキル名。")
    eval_set_path: str = Field(..., description="テストケースファイル（*.evalset.json）の絶対パス、または src ディレクトリからの相対パス。")
    threshold_accuracy: float = Field(1.0, description="合格に必要な精度の閾値（0.0 から 1.0 の浮動小数点）。デフォルトは 1.0 (100%合格)。")
    timeout_seconds: int = Field(180, description="テスト実行のタイムアウト制限（秒）。デフォルトは 180 秒。")
    eval_mode: int = Field(1, description="評価モード。デフォルトは 1。")

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # 既存ロジックが期待するStateパラメータを設定
    tool_context.state["skill_name"] = params.skill_name
    tool_context.state["eval_set_path"] = params.eval_set_path
    tool_context.state["threshold_accuracy"] = params.threshold_accuracy
    tool_context.state["timeout_seconds"] = params.timeout_seconds
    tool_context.state["eval_mode"] = params.eval_mode
    
    # 既存ロジックを呼び出す
    run_test_logic(tool_context)
