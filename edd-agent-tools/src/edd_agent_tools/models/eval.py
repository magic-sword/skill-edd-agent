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


class EDDToolCall(BaseModel):
    """白書 Snippet 3 & Google ADK 2.0 純正準拠の期待されるツール呼び出し定義"""
    tool: str = Field(..., description="呼び出されるべきツール名（ADK 2.0 純正 run_skill_script、またはドメインツール名/スクリプトパス）")
    args: Dict[str, Any] = Field(default_factory=dict, description="期待される引数パラメータ")

    def to_adk_native(self, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """ADK 2.0 純正の {"tool": "run_skill_script", "args": {"skill_name": ..., "file_path": ..., "args": ...}} 形式に正規化します。"""
        if self.tool == "run_skill_script":
            native_args = dict(self.args)
            if skill_name and "skill_name" not in native_args:
                native_args["skill_name"] = skill_name
            return {"tool": "run_skill_script", "args": native_args}

        if self.tool.startswith("scripts/") or self.tool.endswith(".py"):
            resolved_skill = skill_name or self.args.get("skill_name", "")
            file_path = self.tool if self.tool.startswith("scripts/") else f"scripts/{self.tool}"
            inner_args = {k: v for k, v in self.args.items() if k != "skill_name"}
            return {
                "tool": "run_skill_script",
                "args": {
                    "skill_name": resolved_skill,
                    "file_path": file_path,
                    "args": inner_args
                }
            }

        return {"tool": self.tool, "args": self.args}



class EDDTestCase(BaseModel):
    """白書 Snippet 3 準拠の EDD (Evaluation-Driven Development) テストケース"""
    case_id: str = Field(..., description="評価ケースの一意識別子")
    input: str = Field(..., description="エージェントへのユーザ入力プロンプト")
    expected_skill: Optional[str] = Field(None, description="トリガーされるべき期待スキル名")
    expected_tool_calls: List[Union[EDDToolCall, Dict[str, Any], str]] = Field(
        default_factory=list, description="期待されるツール呼び出し軌跡"
    )
    expected_output_format: Optional[str] = Field(None, description="期待される出力フォーマット仕様")
    rubric: List[str] = Field(default_factory=list, description="LLM-as-a-Judge 用の評価ルーブリック項目一覧")


class EvalCase(AdkEvalCase):
    """Google ADK 2.0 純正準拠のテストケース定義（CLI契約テストおよび白書 EDD 複合ケース両対応）"""
    # ADK 純正フィールド (eval_id, conversation, session_input 等) を継承
    eval_case_id: Optional[str] = Field(None, description="テストケース識別ID")
    case_id: Optional[str] = Field(None, description="白書 Snippet 3 準拠のテストケース識別ID")
    input: Optional[str] = Field(None, description="白書 Snippet 3 準拠のユーザ入力プロンプト")
    expected_skill: Optional[str] = Field(None, description="期待スキル名")
    expected_tool_calls: List[Union[EDDToolCall, Dict[str, Any], str]] = Field(default_factory=list, description="期待ツール呼び出し軌跡")
    expected_output_format: Optional[str] = Field(None, description="期待出力フォーマット")
    rubric: List[str] = Field(default_factory=list, description="評価ルーブリック")

    # 従来の CLI 契約テスト用フィールド
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
            # case_id と eval_case_id / eval_id の相互同期
            cid = values.get("case_id") or values.get("eval_case_id") or values.get("eval_id") or "case_0"
            values["case_id"] = cid
            values["eval_case_id"] = cid
            values["eval_id"] = cid

            # input と inputs の同期
            if "input" in values and "user_input" not in values:
                values["user_input"] = values["input"]
            elif "user_input" in values and "input" not in values:
                values["input"] = values["user_input"]

            # ADK ensure_conversation_xor_conversation_scenario を満足させるための互換処理
            has_conv = "conversation" in values and values["conversation"] is not None
            has_scen = "conversation_scenario" in values and values["conversation_scenario"] is not None
            if not has_conv and not has_scen:
                values["conversation"] = []
        return values

    @property
    def is_negative(self) -> bool:
        """白書 Page 22 準拠の負例（スキルがトリガーされてはならない境界ケース）かを判定します。"""
        return self.expected_skill is None or self.expected_skill == ""

    def to_adk_invocation(self, skill_name: Optional[str] = None) -> Any:
        """ADK 2.0 純正の Invocation オブジェクトを構築します。"""
        try:
            from google.genai import types as genai_types
            from google.adk.evaluation.eval_case import Invocation, IntermediateData
        except ImportError:
            return None

        user_text = self.input or (self.inputs.get("query") if isinstance(self.inputs, dict) else "") or ""
        user_content = genai_types.Content(parts=[genai_types.Part.from_text(text=str(user_text))])
        
        final_text = self.expected_output_format or (str(self.expected) if self.expected else "")
        final_resp = genai_types.Content(parts=[genai_types.Part.from_text(text=final_text)], role="model") if final_text else None

        f_calls = []
        resolved_skill = self.expected_skill or skill_name
        for tc in self.expected_tool_calls:
            if isinstance(tc, EDDToolCall):
                d = tc.to_adk_native(skill_name=resolved_skill)
                f_calls.append(genai_types.FunctionCall(name=d["tool"], args=d.get("args", {})))
            elif isinstance(tc, dict):
                t_name = tc.get("tool") or tc.get("name", "")
                t_args = tc.get("args") or {}
                if t_name == "run_skill_script":
                    native_args = dict(t_args)
                    if resolved_skill and "skill_name" not in native_args:
                        native_args["skill_name"] = resolved_skill
                    f_calls.append(genai_types.FunctionCall(name=t_name, args=native_args))
                else:
                    f_calls.append(genai_types.FunctionCall(name=t_name, args=t_args))
            elif isinstance(tc, str):
                f_calls.append(genai_types.FunctionCall(name=tc, args={}))

        inter_data = IntermediateData(tool_uses=f_calls) if f_calls else IntermediateData(tool_uses=[])
        return Invocation(
            invocation_id=self.case_id or self.eval_case_id or "inv_0",
            user_content=user_content,
            final_response=final_resp,
            intermediate_data=inter_data
        )


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

    def to_adk_eval_set(self) -> Any:
        """Google ADK 2.0 純正の EvalSet インスタンスを生成して返します。"""
        if AdkEvalSet is BaseModel:
            return self

        adk_cases = []
        for c in self.eval_cases:
            inv = c.to_adk_invocation(skill_name=self.skill_name)
            try:
                adk_case = AdkEvalCase(
                    eval_id=c.case_id or c.eval_case_id or "case_0",
                    conversation=[inv] if inv else []
                )
                adk_cases.append(adk_case)
            except Exception:
                adk_cases.append(c)

        try:
            return AdkEvalSet(
                eval_set_id=self.eval_set_id,
                name=self.name or self.eval_set_id,
                description=self.description or f"EvalSet for {self.skill_name}",
                eval_cases=adk_cases
            )
        except Exception:
            return self

    def export_adk_evalset_dict(self) -> Dict[str, Any]:
        """ADK 2.0 CLI `adk eval` に直接渡せるネイティブ JSON 辞書形式を出力します。"""
        raw_cases = []
        for c in self.eval_cases:
            user_text = c.input or (c.inputs.get("query") if isinstance(c.inputs, dict) else "") or ""
            final_text = c.expected_output_format or (str(c.expected) if c.expected else "")
            
            tool_uses = []
            resolved_skill = c.expected_skill or self.skill_name
            for tc in c.expected_tool_calls:
                if isinstance(tc, EDDToolCall):
                    tool_uses.append(tc.to_adk_native(skill_name=resolved_skill))
                elif isinstance(tc, dict):
                    t_name = tc.get("tool") or tc.get("name", "")
                    t_args = dict(tc.get("args", {}))
                    if t_name == "run_skill_script" and resolved_skill and "skill_name" not in t_args:
                        t_args["skill_name"] = resolved_skill
                    tool_uses.append({"name": t_name, "args": t_args})
                elif isinstance(tc, str):
                    tool_uses.append({"name": tc, "args": {}})

            raw_cases.append({
                "eval_id": c.case_id or c.eval_case_id or "case_0",
                "conversation": [
                    {
                        "invocation_id": f"inv_{c.case_id or '0'}",
                        "user_content": {
                            "role": "user",
                            "parts": [{"text": str(user_text)}]
                        },
                        "final_response": {
                            "role": "model",
                            "parts": [{"text": final_text}]
                        } if final_text else None,
                        "intermediate_data": {
                            "tool_uses": tool_uses,
                            "intermediate_responses": []
                        }
                    }
                ],
                "session_input": {
                    "app_name": self.skill_name or "default_skill",
                    "user_id": "test_user",
                    "state": {}
                }
            })

        return {
            "eval_set_id": self.eval_set_id,
            "name": self.name or self.eval_set_id,
            "description": self.description or f"EvalSet for {self.skill_name}",
            "eval_cases": raw_cases
        }


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
    failed_cases: List[FailedCaseDetail] = Field(default_factory=list, description="不合格となったテストケース一覧")


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
