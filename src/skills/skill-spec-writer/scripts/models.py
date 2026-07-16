from pydantic import BaseModel, Field
from typing import Literal


class GenerateSkillSpecOutput(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="スキルの実行結果ステータス。'success' または 'failed'。")
    message: str = Field(..., description='実行結果に関する詳細メッセージ。')
    output_dir: str = Field(..., description='仕様書(SKILL.md)が格納されたスキルディレクトリの絶対パス')
