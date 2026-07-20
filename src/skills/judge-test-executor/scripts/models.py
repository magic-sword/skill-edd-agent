from pydantic import BaseModel, Field
from typing import List

class RubricEvaluation(BaseModel):
    criterion: str = Field(..., description="評価された基準の項目名。例: '可読性', 'エラーハンドリング'")
    score: int = Field(..., description="この項目に対する採点（0〜10点）", ge=0, le=10)
    passed: bool = Field(..., description="合格（例: 8点以上）したかどうかの真偽値")
    reason: str = Field(..., description="この採点に至った具体的な理由")

class CaseEvaluation(BaseModel):
    eval_case_id: str = Field(..., description="評価対象のテストケースID")
    rubric_evaluations: List[RubricEvaluation] = Field(..., description="各ルーブリック項目ごとの評価結果リスト")
    passed: bool = Field(..., description="ケース全体として合格（全項目が合格）したかどうかの真偽値")
