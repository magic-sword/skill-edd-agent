from pydantic import BaseModel, Field
from edd_agent_tools.models import PromptField

class Input(BaseModel):
    skill: str = PromptField(..., description='評価対象スキルの名前またはパス。', instructions='評価を実行したいスキルの名前を正確に指定してください。', constraints='必須項目です。既存のスキル名を指定してください。')
    eval_set_path: str | None = PromptField(None, description='テストデータセットファイルのパス。', instructions='評価に使用するテストデータセットファイルのパスを指定してください。省略した場合、対象スキルのデフォルトのトリガー評価セットが使用されます。', constraints="ファイルパス形式で指定してください。例: 'skills/my-skill/evals/trigger/eval_set.jsonl'")
    config_file_path: str | None = Field(None, description='評価設定ファイルのパス。')
    timeout_seconds: int | None = Field(None, description='評価のタイムアウト秒数。')
    threshold_accuracy: float = Field(1.0, ge=0.0, le=1.0, description='合格に必要な精度の閾値（0.0 から 1.0 の浮動小数点）。デフォルトは 1.0。')

class Output(BaseModel):
    value: str = Field(..., description='スキル実行結果の出力メッセージ')