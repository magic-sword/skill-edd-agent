from pydantic import BaseModel, Field
from typing import Literal


class SkillDeveloperOutput(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description='処理結果の成否ステータス。')
    message: str = Field(..., description='処理結果のメッセージサマリー。')
    output_dir: str = Field(..., description='最終生成された成果物が格納されたスキルディレクトリの絶対パス。')
