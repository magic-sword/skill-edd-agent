from pydantic import BaseModel, Field
from typing import Literal

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="検証または評価の結果ステータス。'success' または 'failed'。")
    details: str = Field(..., description='検証/評価の実行結果詳細、不足事項やフィードバック、またはエラーメッセージ。')
    score: float | None = Field(None, ge=0.0, le=1.0, description='検証/評価のスコア（適用可能な場合のみ、0.0〜1.0）。')
