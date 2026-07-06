from pydantic import BaseModel, Field
from typing import Literal

class Input(BaseModel):
    skill: str = Field(..., description='検証対象のスキル名。')

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="検証結果のステータス。'success' または 'failed'。")
    details: str = Field(..., description='検証が失敗した場合の不足事項やフィードバック詳細。成功時は空文字列。')
    score: float = Field(..., ge=0.0, le=1.0, description='設計と実装の整合性スコア（0.0〜1.0）。')
