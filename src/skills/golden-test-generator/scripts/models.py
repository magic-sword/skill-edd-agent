from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class InputParameter(BaseModel):
    name: str = Field(..., description="引数の名前。例: 'a', 'b'")
    value: str = Field(..., description="引数に渡す具体的な値（文字列化された値）。例: '5', '3', '-10'")

class ExpectedToolUse(BaseModel):
    name: str = Field(..., description="呼び出される期待ツールの名前。")
    args: Dict[str, Any] = Field(default_factory=dict, description="ツール呼び出しに渡される期待パラメータ辞書。")

class GoldenCase(BaseModel):
    eval_case_id: str = Field(..., description="テストケースの一意なID。例: case_normal_01")
    function_name: str = Field(..., description="呼び出す関数名。")
    inputs: List[InputParameter] = Field(..., description="関数に引き渡す入力引数リスト。design.jsonで定義されている各引数を必ずこのリストに含めてください。")
    expected_response_rubric: str = Field(..., description="出力が満たすべき意味的基準・チェックリストの説明。LLM-as-Judgeが合否を判定する際の基準文言になります。")
    expected_trajectory: Optional[List[ExpectedToolUse]] = Field(default_factory=list, description="ワークフロー評価時に比較・検証するツール呼び出し経路の期待値シーケンス。")

class GoldenCaseSet(BaseModel):
    eval_set_id: str = Field(..., description="テストケースセットのID")
    eval_cases: List[GoldenCase] = Field(..., description="テストケースのリスト")

