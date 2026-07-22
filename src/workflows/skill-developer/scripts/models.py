from pydantic import BaseModel, Field
from typing import Literal, Optional


class SkillDeveloperOutput(BaseModel):
    status: Literal['success', 'failed', 'halted'] = Field(..., description='処理結果 of 成否ステータス（success, failed, halted）。')
    message: str = Field(..., description='処理結果 of メッセージサマリー。')
    output_dir: Optional[str] = Field(default="", description='最終生成された成果物が格納されたスキルディレクトリ of 絶対パス。')
    proposed_skill: Optional[dict] = Field(default=None, description="要件の難易度が高すぎた場合に提案される事前開発スキルの情報（name, description）。")


