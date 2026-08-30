"""
Evaluation Models for edd-agent-tools
"""

from typing import Dict, Any, List, Optional, Literal, Union
from pydantic import BaseModel, Field
from enum import StrEnum


class ExpectedResultType(StrEnum):
    RETURN_VALUE = "return_value"
    EXCEPTION = "exception"
    CLI_OUTPUT = "cli_output"
    CLI_EXIT_CODE = "cli_exit_code"


class EvalCase(BaseModel):
    """個別のテストケース定義"""
    eval_case_id: str = Field(..., description="テストケース識別ID")
    function_name: Optional[str] = Field(None, description="対象関数名")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="入力引数")
    expected: Any = Field(..., description="期待される出力または例外")
    expected_type: ExpectedResultType = Field(ExpectedResultType.RETURN_VALUE, description="期待結果の検証種別")
    mock_responses: Dict[str, Any] = Field(default_factory=dict, description="モック応答")
    cli_args: Optional[List[str]] = Field(None, description="CLI実行時のコマンドライン引数")
    script_name: Optional[str] = Field(None, description="対象スクリプト名（scripts/配下）")


class EvalCaseSet(BaseModel):
    """スキル評価用テストケースセット"""
    skill_name: str = Field(..., description="対象スキル名")
    test_type: str = Field("contract", description="テスト種別 (contract, trigger, golden, judge, adversarial)")
    eval_cases: List[EvalCase] = Field(default_factory=list, description="テストケース一覧")


class FailedCaseDetail(BaseModel):
    """不合格となったテストケースの詳細情報"""
    eval_case_id: str = Field(..., description="テストケースの一意な識別ID")
    function_name: Optional[str] = Field(None, description="テスト対象となった公開関数名またはスクリプト名")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="テストケース実行時に渡された入力引数")
    expected: str = Field(..., description="期待されていた結果または例外")
    actual: Any = Field(None, description="実際の返却値または発生した例外の文字列表現")
    error_type: Optional[str] = Field(None, description="発生したエラー・例外の型名")
    error_message: Optional[str] = Field(None, description="エラーの詳細メッセージ")
    traceback: Optional[str] = Field(None, description="例外発生時のスタックトレース")


class EvalRunResult(BaseModel):
    """テスト実行サマリー結果"""
    passed: int = Field(..., description="合格したテストの件数")
    failed: int = Field(..., description="不合格だったテストの件数")
    total: int = Field(..., description="テストの総件数")
    accuracy: float = Field(..., description="テストの合格精度（0.0〜1.0）")
    detail_file_path: Optional[str] = Field(None, description="詳細結果JSONファイルの絶対パス")


class EvalDetailReport(BaseModel):
    """テスト実行全体の詳細レポートモデル"""
    skill_name: str = Field(..., description="テスト対象スキルの論理名")
    test_type: str = Field(..., description="実行されたテスト種別")
    timestamp: str = Field(..., description="テスト実行日時のISO 8601文字列")
    passed: int = Field(..., description="合格したテストケース件数")
    failed: int = Field(..., description="不合格だったテストケース件数")
    total: int = Field(..., description="実行された全テストケース件数")
    accuracy: float = Field(..., description="合格精度（0.0〜1.0）")
    details: str = Field("", description="テスト結果のサマリー説明")
    failed_cases: List[FailedCaseDetail] = Field(default_factory=list, description="不合格となったテストケース一覧")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="その他の評価メトリクス")
