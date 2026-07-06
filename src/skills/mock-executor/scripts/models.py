from pydantic import BaseModel, Field

class Input(BaseModel):
    skill: str = Field(..., description='評価対象スキルの名前。')
    eval_set_path: str | None = Field(None, description='テストデータセットファイルのパス。省略時はデフォルトのトリガー評価セットが使用されます。')
    config_file_path: str | None = Field(None, description='評価設定ファイルのパス。')
    timeout_seconds: int | None = Field(None, description='評価のタイムアウト秒数。')
    threshold_accuracy: float = Field(1.0, ge=0.0, le=1.0, description='合格に必要な精度の閾値。デフォルトは 1.0。')

class Output(BaseModel):
    value: str = Field(..., description='スキル実行結果の出力メッセージ')