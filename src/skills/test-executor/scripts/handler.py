from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .logic import process_message as run_logic, run_skill_tests


SKILL_METADATA = {
    "name": "test-executor",
    "description": "指定されたスキルのADK evalテストセットを安全なサブプロセス環境で実行し、ログから算出した精度が合格閾値以上か合否判定します。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill: str = Field(..., description='テスト対象のスキル名。')
    eval_set_path: str = Field(..., description='テストケースファイル（*.evalset.json）の絶対パス、または src ディレクトリからの相対パス。')
    threshold_accuracy: float = Field(1.0, description='合格に必要な精度の閾値（0.0 から 1.0 の浮動小数点）。デフォルトは 1.0 (100%合格)。')
    timeout_seconds: int = Field(180, description='テスト実行のタイムアウト制限（秒）。デフォルトは 180 秒。')
    eval_mode: int = Field(1, description='評価モード。デフォルトは 1。')

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
