"""
Evaluation Models for edd-agent-tools (Google ADK 2.0 Native Integration)

Google ADK 2.0 純正の google.adk.evaluation.eval_set.EvalSet および
google.adk.evaluation.eval_case.EvalCase をシームレスに継承・統合した評価データモデル。
"""

from typing import Dict, Any, List, Optional, Literal, Union
from pydantic import BaseModel, Field, model_validator

# Google ADK 2.0 純正評価モデルのインポート
try:
    from google.adk.evaluation.eval_set import EvalSet as AdkEvalSet
    from google.adk.evaluation.eval_case import (
        EvalCase as AdkEvalCase,
        IntermediateData,
        ToolCallAndResponse,
        Rubric,
        SessionInput,
        SessionState,
        StaticConversation
    )
except ImportError:
    AdkEvalSet = BaseModel
    AdkEvalCase = BaseModel
    IntermediateData = Any
    ToolCallAndResponse = Any
    Rubric = Any
    SessionInput = Any
    SessionState = Any
    StaticConversation = Any


class EvalCase(AdkEvalCase):
    """Google ADK 2.0 純正準拠のテストケース定義（CLI契約テスト拡張対応）"""
    # ADK 純正フィールド (eval_id, conversation, session_input 等) を継承
    eval_case_id: Optional[str] = Field(None, description="テストケース識別ID")
    script_name: Optional[str] = Field(None, description="対象スクリプト名（scripts/配下）またはコマンド")
    cli_args: Optional[List[str]] = Field(default_factory=list, description="CLI実行時のコマンドライン引数")
    expected_exit_code: Optional[int] = Field(0, description="期待されるCLI終了コード")
    expected_stdout_contains: Optional[List[str]] = Field(None, description="標準出力に含まれるべき文字列リスト")
    expected_stderr_contains: Optional[List[str]] = Field(None, description="標準エラー出力に含まれるべき文字列リスト")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="任意の入力パラメータ")
    expected: Optional[Any] = Field(None, description="任意の期待結果")

    @model_validator(mode="before")
    @classmethod
    def normalize_case_and_adk_compatibility(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # eval_id と eval_case_id の相互同期
            if "eval_id" in values and "eval_case_id" not in values:
                values["eval_case_id"] = str(values["eval_id"])
            elif "eval_case_id" in values and "eval_id" not in values:
                values["eval_id"] = str(values["eval_case_id"])
            elif "eval_id" not in values and "eval_case_id" not in values:
                values["eval_id"] = "case_0"
                values["eval_case_id"] = "case_0"

            # ADK ensure_conversation_xor_conversation_scenario を満足させるための互換処理
            has_conv = "conversation" in values and values["conversation"] is not None
            has_scen = "conversation_scenario" in values and values["conversation_scenario"] is not None
            if not has_conv and not has_scen:
                values["conversation"] = []
        return values


class EvalCaseSet(AdkEvalSet):
    """Google ADK 2.0 純正準拠のテストケースセット (EvalSet)"""
    # ADK 純正フィールド (eval_set_id, name, description, eval_cases 等) を継承
    skill_name: Optional[str] = Field(None, description="対象スキル名")
    test_type: Optional[str] = Field("contract", description="テスト種別 (contract, trigger, golden, judge, trajectory, adversarial)")
    eval_cases: List[EvalCase] = Field(default_factory=list, description="テストケース一覧")

    @model_validator(mode="before")
    @classmethod
    def normalize_cases(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "cases" in values and "eval_cases" not in values:
                values["eval_cases"] = values.get("cases", [])
            if "skill_name" not in values and "eval_set_id" in values:
                values["skill_name"] = str(values["eval_set_id"]).split("_")[0]
            if "eval_set_id" not in values:
                values["eval_set_id"] = "default_eval_set"
            if "name" not in values:
                values["name"] = values.get("eval_set_id", "default_eval_set")
        return values


class FailedCaseDetail(BaseModel):
    """不合格となったテストケースの詳細情報"""
    eval_case_id: str = Field(..., description="テストケースの一意な識別ID")
    script_name: Optional[str] = Field(None, description="テスト対象スクリプト名またはコマンド")
    cli_args: Optional[List[str]] = Field(default_factory=list, description="テスト実行時のCLI引数")
    expected: str = Field(..., description="期待されていた結果（終了コードまたは出力内容）")
    actual: Any = Field(None, description="実際の返却値またはエラーの文字列表現")
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
