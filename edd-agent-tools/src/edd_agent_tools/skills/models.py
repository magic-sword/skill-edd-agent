import json
import os
from enum import StrEnum, IntEnum
from pathlib import Path
from typing import Literal, Union, Annotated, Any
from pydantic import BaseModel, Field, TypeAdapter, ConfigDict, model_validator
from edd_agent_tools.schema_utils import PromptField

# ==========================================
# 1. 元の skills/models.py 定義 (skills_state.json 管理用)
# ==========================================

class SkillTier(IntEnum):
    """スキルのセキュリティ・権限階層を定義する列挙型"""
    SANDBOX = 0          # 暫定 / 新規スキルのテスト用
    READ_ONLY = 1        # Read-Only: ファイルの読み込みのみ許可
    DRAFT_ONLY = 2       # Draft-Only: 提案ファイルの作成のみ許可
    ACTION_ALLOWED = 3   # Action-Allowed: すべての実アクションを許可


class SkillEntry(BaseModel):
    """スキルまたはエージェントのディレクトリパス"""
    path: Path = Field(..., description="カスタムスキルフォルダへのパス")
    name: str | None = Field(None, description="探索エントリの論理名（別名）")


class InheritEntry(BaseModel):
    """継承元のマニフェスト定義ファイルパス"""
    path: Path = Field(..., description="継承元の共通マニフェストファイルへのパス")


class ProjectSkillInfo(BaseModel):
    """skills_state.json で管理される各スキル/エージェントのプロジェクト品質メタデータ"""
    tier: SkillTier = Field(SkillTier.SANDBOX, description="スキルの権限階層")


class SkillsStateJson(BaseModel):
    """ADK公式仕様に準拠した、3つの基本フィールドを持つ skills_state.json 用の基本スキーマモデル。

    探索と優先順位のマージ規則:
      1. entries (探索パスの優先順):
         ローカルの entries が最優先され、その後 inherits で指定された継承先の探索パスが順に末尾へ追記されます。
         同名のスキルが複数発見された場合は、探索リストの先頭（ローカル優先）のものがマウントされ、後続はシャドウイング（無視）されます。
      2. inherits (継承元マニフェスト):
         別のマニフェストファイルをインポートし、探索パスを多重解決します。
      3. exclude (除外リストの累積):
         ローカルの除外リストと、すべての継承元で定義された除外リストが累積（論理和マージ）されます。
    """
    entries: list[SkillEntry] = Field(..., description="スキル探索対象のパスリスト")
    inherits: list[InheritEntry] = Field(default_factory=list, description="継承元設定ファイルのリスト")
    exclude: list[str] = Field(default_factory=list, description="除外するスキル名のリスト")

    # プロジェクト独自の拡張メタデータ (論理モジュール名をキーにしたオブジェクトマップ形式)
    skills: dict[str, ProjectSkillInfo] = Field(default_factory=dict, description="登録されている各スキルおよびワークフローの品質ステータス情報")
    agents: dict[str, ProjectSkillInfo] = Field(default_factory=dict, description="登録されている各自律エージェントの品質ステータス情報")


# ==========================================
# 2. 型駆動設計 (Type-Driven Design) による Skill/Workflow設計モデル
# ==========================================

class OutputMode(StrEnum):
    VALUE_ONLY = "VALUE_ONLY"
    CONVERSATIONAL = "CONVERSATIONAL"
    STRUCTURED_JSON = "STRUCTURED_JSON"


class ModuleType(StrEnum):
    SKILL = "skill"
    WORKFLOW = "workflow"


class Parameter(BaseModel):
    name: str = Field(..., description="パラメータの名前")
    type: str = Field(..., description="パラメータの型（例: 'str', 'int', 'bool', 'list'）")
    description: str = Field(..., description="パラメータの説明")
    required: bool = Field(False, description="このパラメータが必須かどうか")
    default: str | None = Field(None, description="パラメータのデフォルト値（任意、文字列等として表現）")
    choices: list[str] | None = Field(None, description="パラメータの有効な選択肢（Literal型アノテーションの生成に使用します）")
    ge: float | None = Field(None, description="数値パラメータの最小値（ge制約の生成に使用します）")
    le: float | None = Field(None, description="数値パラメータの最大値（le制約の生成に使用します）")
    items_type: str | None = Field(None, description="リスト型パラメータの要素の型（例: 'str', 'int'。list[items_type] の生成に使用します）")
    pattern: str | None = Field(None, description="文字列パラメータの正規表現パターン制約（pattern制約の生成に使用します）")
    min_length: int | None = Field(None, description="文字列またはリストパラメータの最小長制約（min_length制約の生成に使用します）")
    max_length: int | None = Field(None, description="文字列またはリストパラメータの最大長制約（max_length制約の生成に使用します）")
    is_prompt_parameter: bool | None = Field(None, description="このパラメータがプロンプト（LLMへの指示）用途かどうか")
    prompt_instructions: str | None = Field(None, description="プロンプトパラメータの有効な指定可能指示ガイドライン")
    prompt_constraints: str | None = Field(None, description="プロンプトパラメータの構造的な制約ガイドライン")
    example: Any | None = Field(None, description="パラメータの正常系テスト用の代表的な入力値例（任意）")


class StepType(StrEnum):
    SKILL = "skill"
    FUNCTION = "function"
    AGENT = "agent"


class Step(BaseModel):
    name: str = Field(..., description="ステップの識別子名")
    type: StepType = Field(..., description="ステップの種別。'skill' (既存スキル), 'function' (カスタムPython関数), 'agent' (自律エージェント)")
    target: str | None = Field(None, description="typeが 'skill' の場合に呼び出す既存のスキル名")
    description: str | None = Field(None, description="typeが 'function' または 'agent' の場合に、ノードの役割・処理要件を記述する説明")
    instruction: str | None = Field(None, description="typeが 'agent' の場合に、エージェントへ与えるシステムプロンプト/指示")
    tools: list[str] | None = Field(None, description="typeが 'agent' の場合に、エージェントが使用可能なツールのリスト")
    inputs: dict[str, str] | None = Field(None, description="引数マッピング辞書。キーはステップに入力される引数名、値は tool_context.state から取得する値（またはPythonの評価式）")


# --- 関数定義モデル (Discriminated by OutputMode) ---

class PrimitiveFunctionDefinition(BaseModel):
    """output_mode が VALUE_ONLY または CONVERSATIONAL の場合の関数定義モデル。
    response_type のみを持ち、response_parameters は型レベルで存在しません。
    """
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="公開関数名。小文字のスネークケース")
    description: str = Field(..., description="関数の役割や目的の説明")
    parameters: list[Parameter] = Field(..., description="関数の入力パラメータリスト")
    response_type: str | None = Field("str", description="関数が返す単一のプリミティブ型（例: 'str', 'int', 'bool', 'list[str]', 'EvalRunResult' など）")


class StructuredFunctionDefinition(BaseModel):
    """output_mode が STRUCTURED_JSON の場合の関数定義モデル。
    response_parameters のみを持ち、response_type は型レベルで存在しません。
    """
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="公開関数名。小文字のスネークケース")
    description: str = Field(..., description="関数の役割や目的の説明")
    parameters: list[Parameter] = Field(..., description="関数の入力パラメータリスト")
    response_parameters: list[Parameter] = Field(..., description="関数の構造化出力パラメータ定義リスト")


FunctionDefinition = Union[StructuredFunctionDefinition, PrimitiveFunctionDefinition]


# --- スキル設計モデル ---

class BaseSkillDesign(BaseModel):
    rationale: str = Field(..., description="設計の思考プロセス。")
    name: str = Field(..., description="スキルの名前。小文字のハイフン区切り")
    description: str = Field(..., description="スキルの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="スキルの仕様概要")
    module_type: Literal[ModuleType.SKILL] = Field(ModuleType.SKILL, description="モジュールの役割分類。単一スキルは必ず 'skill'")
    execution_type: Literal["tool", "agent"] = Field(..., description="実行タイプ。'tool' (スクリプト処理) または 'agent' (LLM推論)")
    dependencies: list[str] = Field([], description="スキルが依存する他のスキルのリスト")
    constraints: list[str] = Field([], description="モデルバリデータ等から抽出された制約条件のリスト")


class ValueOnlySkillDesign(BaseSkillDesign):
    """output_mode が VALUE_ONLY または CONVERSATIONAL の単一スキル設計モデル。"""
    output_mode: Literal[OutputMode.VALUE_ONLY, OutputMode.CONVERSATIONAL] = Field(OutputMode.VALUE_ONLY, description="出力形式")
    functions: list[PrimitiveFunctionDefinition] = Field(..., description="単一戻り値関数定義のリスト")


class StructuredJsonSkillDesign(BaseSkillDesign):
    """output_mode が STRUCTURED_JSON の単一スキル設計モデル。"""
    output_mode: Literal[OutputMode.STRUCTURED_JSON] = Field(OutputMode.STRUCTURED_JSON, description="出力形式")
    functions: list[StructuredFunctionDefinition] = Field(..., description="構造化出力関数定義のリスト")


class SkillDesign(BaseModel):
    """単一スキルの設計定義を表す Pydantic モデル（型安全ディスパッチャー兼後方互換インターフェース）。"""

    @classmethod
    def load_from_file(cls, filepath: str) -> "Union[StructuredJsonSkillDesign, ValueOnlySkillDesign, WorkflowDesign]":
        return load_design_from_file(filepath)

    @model_validator(mode="wrap")
    @classmethod
    def _validate(cls, value, handler):
        if isinstance(value, (StructuredJsonSkillDesign, ValueOnlySkillDesign)):
            return value
        if isinstance(value, dict):
            out_mode = value.get("output_mode", OutputMode.VALUE_ONLY)
            if out_mode == OutputMode.STRUCTURED_JSON:
                return StructuredJsonSkillDesign.model_validate(value)
            else:
                return ValueOnlySkillDesign.model_validate(value)
        return handler(value)


# --- ワークフロー設計モデル ---

class WorkflowDesign(BaseModel):
    """複数モジュールを連結するワークフローの設計仕様定義。"""
    rationale: str = Field(..., description="設計の思考プロセス。")
    name: str = Field(..., description="ワークフローの名前。小文字のハイフン区切り")
    description: str = Field(..., description="ワークフローの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="ワークフローの仕様概要")
    module_type: Literal[ModuleType.WORKFLOW] = Field(ModuleType.WORKFLOW, description="モジュールの役割分類。ワークフローは必ず 'workflow'")
    parameters: list[Parameter] = Field(..., description="ワークフロー全体が外部から受け取るパラメータのリスト")
    dependencies: list[str] = Field([], description="依存するターゲットスキル名のリスト")
    constraints: list[str] = Field([], description="全体の実行に関する制約")
    response_parameters: list[Parameter] | None = Field(None, description="全体の出力JSONの構造定義（STRUCTURED_JSON時に使用）")
    steps: list[Step] = Field(..., description="ワークフローを構成するステップの定義リスト（有向グラフ）")

    @classmethod
    def load_from_file(cls, filepath: str) -> "WorkflowDesign":
        res = load_design_from_file(filepath)
        if not isinstance(res, WorkflowDesign):
            raise TypeError(f"Expected WorkflowDesign but got {type(res).__name__}")
        return res


# --- モジュール統合設計モデル ---

ModuleDesign = Union[StructuredJsonSkillDesign, ValueOnlySkillDesign, WorkflowDesign]


def load_design_from_file(filepath: str) -> Union[StructuredJsonSkillDesign, ValueOnlySkillDesign, WorkflowDesign]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"design.json not found at: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.loads(f.read())
        
    m_type = data.get("module_type", ModuleType.SKILL)
    if m_type == ModuleType.WORKFLOW:
        return WorkflowDesign.model_validate(data)
    
    out_mode = data.get("output_mode", OutputMode.VALUE_ONLY)
    if out_mode == OutputMode.STRUCTURED_JSON:
        return StructuredJsonSkillDesign.model_validate(data)
    else:
        return ValueOnlySkillDesign.model_validate(data)


class SkillMetadata(BaseModel):
    """レジストリ情報と設計仕様情報をマージした、スキルの統合メタデータ"""
    name: str = Field(..., description="スキル名")
    tier: int = Field(0, description="スキルのTier（0から3）", ge=0, le=3)
    last_tested: str | None = Field(None, description="最後にテストされた時刻")
    module_type: ModuleType = Field(ModuleType.SKILL, description="モジュールの役割分類（'skill' または 'workflow'）")
    execution_type: Literal["tool", "agent"] = Field("tool", description="実行タイプ。'tool' または 'agent'")
    description: str = Field("", description="スキルの目的や説明")
    dependencies: list[str] = Field([], description="依存スキルのリスト")
