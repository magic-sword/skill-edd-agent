from pydantic import BaseModel, Field
from typing import Literal


class RunFirstTestOutput(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description='ワークフローの実行結果。')
    message: str = Field(..., description='実行結果のサマリー、または不合格テストや検証エラーの詳細。')
    registered: bool = Field(..., description='対象スキルがSkillsStateにTier 1として登録されたかどうかの真偽値。')
