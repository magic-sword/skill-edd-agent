from pydantic import BaseModel, Field
from typing import Literal


class SkillDesignerOutput(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="処理結果の成否ステータス（'success' / 'failed'）")
    message: str = Field(..., description='処理結果のメッセージサマリー')
    output_dir: str = Field(..., description='成果物(design.json)が格納されたスキルディレクトリの絶対パス')
