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
    """Google ADK 2.0 純正 run_skill_script 呼び出しモデル"""
    name: str = Field(default="run_skill_script", description="ツール名 (Google ADK 2.0 純正 run_skill_script)")
    args: Dict[str, Any] = Field(default_factory=dict, description="引数パラメータ (skill_name, file_path, args)")

    def to_adk_native(self, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """ADK 2.0 純正の {"name": "run_skill_script", "args": {...}} 形式を返します。"""
        native_args = dict(self.args)
        if skill_name and "skill_name" not in native_args:
            native_args["skill_name"] = skill_name
        return {"name": self.name, "args": native_args}


class EvalCase(AdkEvalCase):
    """Google ADK 2.0 純正準拠のテストケース定義。
    
    AdkEvalCase (eval_id, conversation, session_input, rubrics) を第一級の単一真実源 (SSOT) とし、
    余計なレガシーフィールドの二重管理・偽判定コードを完全に排除した純粋な設計を提供します。
    """

    @model_validator(mode="before")
    @classmethod
    def normalize_eval_case(cls, values: Any) -> Any:
        """レガシーキー（case_id, input 等）を ADK 2.0 公式 EvalCase スキーマに透過正規化します。"""
        if isinstance(values, dict):
            # 1. eval_id の正規化
            if "eval_id" not in values:
                values["eval_id"] = values.get("case_id") or values.get("eval_case_id") or values.get("id") or "case_001"

            # 2. rubrics の正規化
            if "rubrics" not in values and "rubric" in values:
                raw_rubrics = values.pop("rubric")
                if isinstance(raw_rubrics, list):
                    values["rubrics"] = [
                        {"rubric_id": f"r_{idx+1}", "rubric_content": {"text_property": r}} if isinstance(r, str) else r
                        for idx, r in enumerate(raw_rubrics)
                    ]

            # 3. conversation の自動構築 (ADK 2.0 の ensure_conversation_xor_conversation_scenario 充足)
            if "conversation" not in values and "conversation_scenario" not in values:
                user_text = values.get("input") or values.get("user_input") or ""
                final_text = values.get("expected_output_format") or values.get("expected_output") or ""
                inter = values.get("intermediate_data")
                if isinstance(inter, dict) and "tool_uses" in inter:
                    tool_calls = inter.get("tool_uses") or []
                else:
                    tool_calls = values.get("expected_tool_calls") or []

                tool_uses = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        t_name = tc.get("name") or tc.get("tool") or "run_skill_script"
                        t_args = tc.get("args") or {}
                        tool_uses.append({"name": t_name, "args": t_args})
                    elif isinstance(tc, str):
                        tool_uses.append({"name": tc, "args": {}})
                    else:
                        tool_uses.append(tc)

                invocation = {
                    "invocation_id": f"inv_{values['eval_id']}",
                    "user_content": {"role": "user", "parts": [{"text": str(user_text)}]},
                    "final_response": {"role": "model", "parts": [{"text": str(final_text)}]} if final_text else None,
                    "intermediate_data": {
                        "tool_uses": tool_uses,
                        "intermediate_responses": []
                    }
                }
                values["conversation"] = [invocation]

        return values

    @property
    def eval_case_id(self) -> str:
        """eval_id のプロパティ"""
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
        """期待されるツール呼び出し一覧（ADK 公式 get_all_tool_calls を活用）"""
        if self.conversation and len(self.conversation) > 0:
            inv = self.conversation[0]
            if inv.intermediate_data:
                try:
                    from google.adk.evaluation.eval_case import get_all_tool_calls
                    calls = get_all_tool_calls(inv.intermediate_data)
                    if calls:
                        return calls
                except Exception:
                    pass
                if hasattr(inv.intermediate_data, "tool_uses"):
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
        """expected_tool_calls (ADK run_skill_script) から対象スクリプトパスを導出"""
        for tc in self.expected_tool_calls:
            t_name = tc.get("name") or tc.get("tool", "") if isinstance(tc, dict) else getattr(tc, "name", str(tc))
            t_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            if t_name == "run_skill_script" and isinstance(t_args, dict):
                return t_args.get("file_path")
            if t_name.startswith("scripts/") or t_name.endswith(".py") or t_name.endswith(".sh") or t_name.endswith(".bash"):
                return t_name
        return None

    @property
    def cli_args(self) -> List[str]:
        """expected_tool_calls から CLI 引数リストを導出"""
        for tc in self.expected_tool_calls:
            t_name = tc.get("name") or tc.get("tool", "") if isinstance(tc, dict) else getattr(tc, "name", str(tc))
            t_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            if t_name == "run_skill_script" and isinstance(t_args, dict):
                args_list = []
                # 1. args (long options) または 引数リスト
                inner_args = t_args.get("args")
                if inner_args is None:
                    inner_args = {k: v for k, v in t_args.items() if k not in ("skill_name", "file_path", "positional_args", "short_options")}
                if isinstance(inner_args, list):
                    args_list.extend([str(a) for a in inner_args])
                else:
                    if isinstance(inner_args, dict):
                        for k, v in inner_args.items():
                            flag = f"--{k.replace('_', '-')}" if not k.startswith("-") else k
                            if v is True:
                                args_list.append(flag)
                            elif v is not False and v is not None:
                                args_list.extend([flag, str(v)])
                    # 2. short_options
                    short_opts = t_args.get("short_options") or {}
                    if isinstance(short_opts, dict):
                        for sk, sv in short_opts.items():
                            s_flag = f"-{sk}" if not sk.startswith("-") else sk
                            if sv is True:
                                args_list.append(s_flag)
                            elif sv is not False and sv is not None:
                                args_list.extend([s_flag, str(sv)])
                    # 3. positional_args (ADK 2.0 公式 RunSkillScriptTool 準拠: '--' で区切って末尾に追加)
                    pos_args = t_args.get("positional_args") or []
                    if isinstance(pos_args, list) and pos_args:
                        args_list.append("--")
                        args_list.extend([str(p) for p in pos_args])
                return args_list

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
            elif t_args:
                return [str(t_args)]
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
