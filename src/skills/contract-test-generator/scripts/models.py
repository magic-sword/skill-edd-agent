from pydantic import BaseModel, Field


class GenerateTestCasesOutput(BaseModel):
    success: bool = Field(..., description='テストケースの生成と書き出しが成功したかどうか。')
