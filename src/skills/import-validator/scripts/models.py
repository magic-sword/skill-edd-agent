from pydantic import BaseModel, Field
from typing import Literal

class Input(BaseModel):
    skill: str = Field(..., description='動的インポートを検証する対象のスキル名。')

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="スキルの動的ロードの成否。'success' または 'failed'。")
    details: str = Field(..., description='動的ロードが失敗した場合のエラー詳細（トレースバックなど）。成功時は空文字列。')
    score: float | None = Field(None, ge=0.0, le=1.0, description='動的ロード検証のスコア（成功時は 1.0、失敗時は 0.0）。')
