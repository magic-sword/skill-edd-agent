from pydantic import BaseModel, Field
from typing import Literal


class Tier2TestRunnerOutput(BaseModel):
    status: Literal['success', 'failed'] = Field(..., description="実行結果のステータス。'success' または 'failed'")
    message: str = Field(..., description='実行結果の詳細メッセージ')
    registered: bool = Field(..., description='登録が成功したかどうかの真偽値')
