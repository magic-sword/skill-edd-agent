from pydantic import BaseModel, Field

class RunFirstTestOutput(BaseModel):
    status: str = Field(..., description="実行結果のステータス。'success' または 'failed'")
    message: str = Field(..., description="実行結果のメッセージ詳細")
    registered: bool = Field(..., description="登録が成功したかどうかの真偽値")
