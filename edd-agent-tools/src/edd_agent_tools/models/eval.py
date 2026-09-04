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
    """Google ADK 2.0 純正 run_skill_script および白書ツール呼び出しの正規化モデル"""
    tool: str = Field(..., description="呼び出されるべきツール名（ADK 2.0 純正 run_skill_script、またはドメインツール名/スクリプトパス）")
    args: Dict[str, Any] = Field(default_factory=dict, description="期待される引数パラメータ")

    def to_adk_native(self, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """ADK 2.0 純正の {"name": "run_skill_script", "args": {"skill_name": ..., "file_path": ..., "args": ...}} 形式に正規化します。"""
        if self.tool == "run_skill_script":
            native_args = dict(self.args)
            if skill_name and "skill_name" not in native_args:
                native_args["skill_name"] = skill_name
            return {"name": "run_skill_script", "tool": "run_skill_script", "args": native_args}

        if self.tool.startswith("scripts/") or self.tool.endswith(".py"):
            resolved_skill = skill_name or self.args.get("skill_name", "")
            file_path = self.tool if self.tool.startswith("scripts/") else f"scripts/{self.tool}"
            inner_args = {k: v for k, v in self.args.items() if k != "skill_name"}
            return {
                "name": "run_skill_script",
                "tool": "run_skill_script",
                "args": {
                    "skill_name": resolved_skill,
                    "file_path": file_path,
                    "args": inner_args
                }
            }

        return {"name": self.tool, "tool": self.tool, "args": self.args}


class EvalCase(AdkEvalCase):
    """Google ADK 2.0 純正準拠のテストケース定義。
    
    AdkEvalCase (eval_id, conversation, session_input, rubrics) を第一級の単一真実源 (SSOT) とし、
    余計なレガシーフィールドの二重管理を排除した純粋な設計を提供します。
    """
    # 下位互換用オプショナルフィールド（ADK 2.0 では eval_id および intermediate_data.tool_uses が SSOT）
    case_id: Optional[str] = Field(None, description="[非推奨] テストケース識別ID (eval_id のエイリアス)")
    expected_skill: Optional[str] = Field(None, description="[非推奨] 期待スキル名 (ADK 2.0 では tool_uses の有無で判定)")

    @model_validator(mode="before")
    @classmethod
    def normalize_case_and_adk_compatibility(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # eval_id と case_id の同期
            cid = values.get("eval_id") or values.get("case_id") or values.get("eval_case_id") or "case_0"
            values["eval_id"] = cid
            values["case_id"] = cid

            raw_inp = values.get("input") or values.get("user_input")
            raw_tools = values.get("expected_tool_calls")
            raw_out = values.get("expected_output_format")
            raw_rub = values.get("rubric") or values.get("rubrics")

            conv = values.get("conversation")
            if not conv and (raw_inp or raw_tools is not None):
                try:
                    from google.genai import types as genai_types
                    from google.adk.evaluation.eval_case import Invocation, IntermediateData
                    from google.adk.evaluation.eval_rubrics import Rubric as AdkRubric

                    u_content = genai_types.Content(parts=[genai_types.Part.from_text(text=str(raw_inp or ""))], role="user")
                    f_resp = genai_types.Content(parts=[genai_types.Part.from_text(text=str(raw_out or ""))], role="model") if raw_out else None

                    f_calls = []
                    skill_target = values.get("expected_skill")
                    for tc in (raw_tools or []):
                        if isinstance(tc, dict):
                            t_name = tc.get("tool") or tc.get("name", "")
                            t_args = dict(tc.get("args", {}))
                            if t_name == "run_skill_script" and skill_target and "skill_name" not in t_args:
                                t_args["skill_name"] = skill_target
                            elif t_name.startswith("scripts/") or t_name.endswith(".py"):
                                rel_path = t_name if t_name.startswith("scripts/") else f"scripts/{t_name}"
                                inner_args = {k: v for k, v in t_args.items() if k != "skill_name"}
                                t_name = "run_skill_script"
                                t_args = {"skill_name": skill_target or "", "file_path": rel_path}
                                if inner_args:
                                    t_args["args"] = inner_args
                            f_calls.append(genai_types.FunctionCall(name=t_name, args=t_args))
                        elif isinstance(tc, str):
                            f_calls.append(genai_types.FunctionCall(name=tc, args={}))

                    inter_data = IntermediateData(tool_uses=f_calls)
                    values["conversation"] = [
                        Invocation(
                            invocation_id=f"inv_{cid}",
                            user_content=u_content,
                            final_response=f_resp,
                            intermediate_data=inter_data
                        )
                    ]

                    if raw_rub and isinstance(raw_rub, list):
                        rubric_objs = []
                        for i, r in enumerate(raw_rub, 1):
                            if isinstance(r, str):
                                rubric_objs.append(AdkRubric(rubric_id=f"r_{i}", rubric_content={"text_property": r}, type="FINAL_RESPONSE_QUALITY"))
                            elif isinstance(r, dict) and "rubric_id" in r:
                                rubric_objs.append(AdkRubric.model_validate(r))
                        values["rubrics"] = rubric_objs
                except Exception:
                    values["conversation"] = []

            # ADK ensure_conversation_xor_conversation_scenario を満たす処理
            has_conv = "conversation" in values and values["conversation"] is not None
            has_scen = "conversation_scenario" in values and values["conversation_scenario"] is not None
            if not has_conv and not has_scen:
                values["conversation"] = []

        return values

    @property
    def eval_case_id(self) -> str:
        """eval_id のエイリアス"""
        return self.eval_id

    @property
    def input(self) -> str:
        """ユーザ入力プロンプト（conversation[0] から取得）"""
        if self.conversation and len(self.conversation) > 0:
            inv = self.conversation[0]
            if inv.user_content and inv.user_content.parts:
                part = inv.user_content.parts[0]
                return getattr(part, "text", "") or ""
        return ""

    @property
    def user_input(self) -> str:
        """input のエイリアス"""
        return self.input

    @property
    def expected_tool_calls(self) -> List[Any]:
        """期待されるツール呼び出し一覧（conversation[0].intermediate_data.tool_uses から取得）"""
        if self.conversation and len(self.conversation) > 0:
            inv = self.conversation[0]
            if inv.intermediate_data and hasattr(inv.intermediate_data, "tool_uses"):
                return inv.intermediate_data.tool_uses or []
        return []

    @property
    def expected_output_format(self) -> Optional[str]:
        """期待される出力フォーマット（final_response から取得）"""
        if self.conversation and len(self.conversation) > 0:
            inv = self.conversation[0]
            if inv.final_response and inv.final_response.parts:
                part = inv.final_response.parts[0]
                return getattr(part, "text", "") or None
        return None

    @property
    def rubric(self) -> List[str]:
        """評価ルーブリック項目一覧（rubrics から文字列リストとして抽出）"""
        if self.rubrics:
            res = []
            for r in self.rubrics:
                if isinstance(r, str):
                    res.append(r)
                elif hasattr(r, "rubric_content") and getattr(r.rubric_content, "text_property", None):
                    res.append(r.rubric_content.text_property)
                elif isinstance(r, dict) and "rubric_content" in r:
                    res.append(r["rubric_content"].get("text_property", str(r)))
            return res
        return []

    @property
    def script_name(self) -> Optional[str]:
        """expected_tool_calls (ADK run_skill_script) から対象スクリプト名を導出"""
        for tc in self.expected_tool_calls:
            t_name = tc.get("name") or tc.get("tool", "") if isinstance(tc, dict) else getattr(tc, "name", str(tc))
            t_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            if t_name == "run_skill_script" and isinstance(t_args, dict):
                return t_args.get("file_path")
            if t_name.startswith("scripts/") or t_name.endswith(".py"):
                return t_name
        return None

    @property
    def cli_args(self) -> List[str]:
        """expected_tool_calls から CLI 引数リストを導出"""
        for tc in self.expected_tool_calls:
            t_name = tc.get("name") or tc.get("tool", "") if isinstance(tc, dict) else getattr(tc, "name", str(tc))
            t_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            if t_name == "run_skill_script" and isinstance(t_args, dict):
                inner_args = t_args.get("args")
                if inner_args is None:
                    inner_args = {k: v for k, v in t_args.items() if k not in ("skill_name", "file_path")}
                t_args = inner_args

            if isinstance(t_args, dict):
                args_list = []
                for k, v in t_args.items():
                    flag = f"--{k.replace('_', '-')}" if not k.startswith("-") else k
                    if v is True:
                        args_list.append(flag)
                    elif v is not False and v is not None:
                        args_list.extend([flag, str(v)])
                return args_list
            elif isinstance(t_args, list):
                return [str(a) for a in t_args]
        return []

    @property
    def expected_exit_code(self) -> int:
        """期待終了コード (0)"""
        return 0

    @property
    def expected_stdout_contains(self) -> Optional[List[str]]:
        """期待標準出力キーワードリスト（expected_output_format から導出）"""
        fmt = self.expected_output_format
        abstract_suffixes = (
            "_format",
            "_summary",
            "_calculation",
            "_id",
            "_help",
            "_confirmation",
            "_path",
            "_status",
            "_report",
            "_result",
            "_output",
            "_response",
            "_data",
            "_message"
        )
        if fmt and not fmt.endswith(abstract_suffixes):
            return [fmt]
        return None

    @property
    def is_negative(self) -> bool:
        """白書 Page 22 準拠の負例（ツール呼び出しが不要な境界ケース）かを判定します。"""
        return len(self.expected_tool_calls) == 0

    def to_adk_invocation(self, skill_name: Optional[str] = None) -> Any:
        """ADK 2.0 純正の Invocation オブジェクトを返します。"""
        if self.conversation and len(self.conversation) > 0:
            return self.conversation[0]
        return None


class EvalCaseSet(AdkEvalSet):
    """Google ADK 2.0 純正準拠のテストケースセット (EvalSet)"""
    skill_name: Optional[str] = Field(None, description="対象スキル名")
    eval_cases: List[EvalCase] = Field(default_factory=list, description="テストケース一覧")

    @property
    def cases(self) -> List[EvalCase]:
        """eval_cases のエイリアス"""
        return self.eval_cases

    @cases.setter
    def cases(self, val: List[EvalCase]) -> None:
        self.eval_cases = val

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
        return self


# Google ADK 2.0 純正 google.adk.evaluation.eval_set.EvalSet / EvalCase との完全互換エイリアス
EvalSet = EvalCaseSet

EDDTestCase = EvalCase


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
