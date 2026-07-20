from pydantic import BaseModel, Field
from typing import List

class InputParameter(BaseModel):
    name: str = Field(..., description="引数の名前。例: 'a', 'b'")
    value: str = Field(..., description="引数に渡す具体的な値（文字列化された値）。例: '5', '3', '-10'")

class GoldenCase(BaseModel):
    eval_case_id: str = Field(..., description="テストケースの一意なID。例: case_normal_01")
    function_name: str = Field(..., description="呼び出す関数名。")
    inputs: List[InputParameter] = Field(..., description="関数に引き渡す入力引数リスト。design.jsonで定義されている各引数を必ずこのリストに含めてください。")
    expected_response_rubric: str = Field(..., description="出力が満たすべき意味的基準・チェックリストの説明。LLM-as-Judgeが合否を判定する際の基準文言になります。")

class GoldenCaseSet(BaseModel):
    eval_set_id: str = Field(..., description="テストケースセットのID")
    eval_cases: List[GoldenCase] = Field(..., description="テストケースのリスト")
