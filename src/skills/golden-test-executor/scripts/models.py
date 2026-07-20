from pydantic import BaseModel, Field

class JudgeResult(BaseModel):
    score: int = Field(..., description="ルーブリックへの適合度を表すスコア（0点から10点まで）", ge=0, le=10)
    reason: str = Field(..., description="このスコアリングを行った具体的な判定理由の説明")
    passed: bool = Field(..., description="合格基準（8点以上）を満たしているかどうかの真偽値")
