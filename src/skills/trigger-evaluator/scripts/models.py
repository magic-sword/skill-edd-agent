from pydantic import BaseModel, Field

class StaticEvalResult(BaseModel):
    specificity: int = Field(..., description="トリガー条件の具体性を1-5の整数で評価したもの")
    clarity: int = Field(..., description="トリガー条件の明確性を1-5の整数で評価したもの")

class TriggerTestCases(BaseModel):
    positive_prompts: list[str] = Field(
        ...,
        description="このスキルがトリガーされるべき陽性プロンプト（10件）"
    )
    negative_prompts: list[str] = Field(
        ...,
        description="このスキルとは関係のない一般的な雑談などの陰性プロンプト（10件）"
    )
