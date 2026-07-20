from pydantic import BaseModel, Field

class RunTier2TestOutput(BaseModel):
    status: str = Field(..., description="実行結果のステータス。'success' または 'failed'")
    message: str = Field(..., description="実行結果の詳細メッセージ")
    registered: bool = Field(..., description="Tier 2 として登録が成功したかどうかの真偽値")
