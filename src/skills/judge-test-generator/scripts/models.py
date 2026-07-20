from pydantic import BaseModel, Field
from typing import List

class InputParameter(BaseModel):
    name: str = Field(..., description="引数の名前。例: 'a', 'b'")
    value: str = Field(..., description="引数に渡す具体的な値（文字列化された値）。例: '5', '3'")

class RubricItem(BaseModel):
    criterion: str = Field(..., description="評価基準の項目名。例: '可読性', '堅牢性', '仕様適合度'")
    description: str = Field(..., description="合格とするための詳細な評価基準。例: '計算された合計が正確な整数であること'")
    weight: float = Field(..., description="この評価項目の配点（全体のスコア計算時の重み）。例: 1.0, 0.5")

class JudgeCase(BaseModel):
    eval_case_id: str = Field(..., description="テストケースの一意なID。例: case_judge_01")
    function_name: str = Field(..., description="呼び出す関数名。")
    inputs: List[InputParameter] = Field(..., description="関数に引き渡す入力引数リスト。design.jsonで定義されている各引数を必ず含めてください。")
    rubrics: List[RubricItem] = Field(..., description="このケースの出力が満たすべき多角的な評価ルーブリック項目リスト。")

class JudgeCaseSet(BaseModel):
    eval_set_id: str = Field(..., description="テストケースセットのID")
    eval_cases: List[JudgeCase] = Field(..., description="テストケースのリスト")
