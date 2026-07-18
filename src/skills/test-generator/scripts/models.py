from pydantic import BaseModel, Field
from typing import Literal


class GenerateTestCasesOutput(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="テスト生成の成否 ('success' または 'failed')。")
    message: str = Field(..., description='テスト生成処理のサマリーメッセージ。')
    eval_set_path: str = Field(..., description='生成されたテストケースJSONファイルの絶対パス。')
