from pydantic import BaseModel, Field


class AddNumbersOutput(BaseModel):
    value: str = Field(..., description='実行結果の出力メッセージ')
