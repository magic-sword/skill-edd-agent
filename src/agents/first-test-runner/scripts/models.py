from pydantic import BaseModel, Field
from typing import Literal

class Input(BaseModel):
    skill: str = Field(..., description='試験対象のスキル名。')
    threshold_accuracy: float = Field(1.0, ge=0.0, le=1.0, description='合格に必要な精度の閾値（0.0 から 1.0）。デフォルトは 1.0。')

class Output(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="ワークフローの実行結果。'success' または 'failed'。")
    message: str = Field(..., description='実行結果のサマリー、または不合格テストや検証エラーの詳細。')
    registered: bool = Field(..., description='対象スキルがSkillsStateにTier 1として登録されたかどうかの真偽値。')
