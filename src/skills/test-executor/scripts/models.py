from pydantic import BaseModel, Field

class Input(BaseModel):
    skill: str = Field(..., description='評価対象スキルの名前。')
    eval_set_path: str = Field('trigger', description="評価セットの識別子（'trigger' または 'unit'）、あるいはファイルパス。デフォルトは 'trigger'。")
    config_file_path: str | None = Field(None, description='評価設定ファイルのパス。指定しない場合は自動解決・自動生成されます。')
    timeout_seconds: int = Field(180, description='評価のタイムアウト秒数。デフォルトは 180 秒。')
    threshold_accuracy: float = Field(1.0, ge=0.0, le=1.0, description='合格に必要な精度の閾値（0.0 から 1.0）。デフォルトは 1.0。')

from typing import Literal

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="検証または評価の結果ステータス。'success' または 'failed'。")
    details: str = Field(..., description='検証/評価の実行結果詳細、不足事項やフィードバック、またはエラーメッセージ。')
    score: float | None = Field(None, ge=0.0, le=1.0, description='検証/評価のスコア（適用可能な場合のみ、0.0〜1.0）。')
