from pydantic import BaseModel, Field

class Input(BaseModel):
    skill: str = Field(..., description="評価対象スキルの名前またはパス。")
    eval_set_path: str | None = Field(None, description="テストデータセットファイルのパス。")
    config_file_path: str | None = Field(None, description="評価設定ファイルのパス。")
    timeout_seconds: int | None = Field(None, description="評価のタイムアウト秒数。")
    threshold_accuracy: float | None = Field(1.0, description="合格に必要な精度の閾値（0.0 から 1.0 の浮動小数点）。デフォルトは 1.0。")
