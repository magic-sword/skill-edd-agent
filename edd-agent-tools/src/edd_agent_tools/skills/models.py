import json
import os
from enum import StrEnum, IntEnum
from pathlib import Path
from typing import Literal, Union, Annotated, Any
from pydantic import BaseModel, Field, model_validator, TypeAdapter
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
# 2. 旧 root models.py から移動された定義 (Skill/Workflow設計用)
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


class FunctionDefinition(BaseModel):
    """複数公開関数を設計する場合の、個別関数の定義情報を表すモデル。"""
    name: str = Field(..., description="公開関数名。小文字のスネークケース")
    description: str = Field(..., description="関数の役割や目的の説明")
    parameters: list[Parameter] = Field(..., description="関数の入力パラメータリスト")
    response_parameters: list[Parameter] | None = Field(None, description="関数の構造化出力パラメータ定義（STRUCTURED_JSON時に使用されます）")
    response_type: str | None = Field(None, description="output_mode が VALUE_ONLY または CONVERSATIONAL の場合に、関数が返すプリミティブな型（例: 'str', 'int', 'bool', 'list[str]' など。任意）")


class SkillDesign(BaseModel):
    """単一スキルの設計定義を表す Pydantic モデル。"""
    rationale: str = Field(..., description="設計の思考プロセス。要件の難易度・必要な手順を詳細に分析し、なぜ workflow ではなくアトミックな単一の skill と判定したかの設計根拠を記述してください。")
    name: str = Field(..., description="スキルの名前。小文字のハイフン区切り")
    description: str = Field(..., description="スキルの目的や役割を記述した簡潔な説明（L1 description用）")
    summary: str | None = Field(None, description="スキルの仕様概要")
    module_type: Literal[ModuleType.SKILL] = Field(ModuleType.SKILL, description="モジュールの役割分類。単一スキルは必ず 'skill'")
    execution_type: Literal["tool", "agent"] = Field(..., description="実行タイプ。'tool' (スクリプト処理) または 'agent' (LLM推推推論)")
    output_mode: OutputMode = Field(..., description="出力形式（VALUE_ONLY, CONVERSATIONAL, STRUCTURED_JSON）")
    dependencies: list[str] = Field([], description="スキルが依存する他のスキルのリスト")
    constraints: list[str] = Field([], description="モデルバリデータ等から抽出された制約条件のリスト")
    functions: list[FunctionDefinition] = Field(..., description="スキルパッケージが提供する公開関数の定義リスト。1つ以上の関数定義を含める必要があります")

    @model_validator(mode="after")
    def validate_response_parameters(self) -> "SkillDesign":
        for fn in self.functions:
            if self.output_mode != OutputMode.STRUCTURED_JSON:
                if fn.response_parameters:
                    raise ValueError("Function-level response_parameters can only be defined when output_mode is 'STRUCTURED_JSON'")
            else:
                if fn.response_type:
                    raise ValueError("Function-level response_type cannot be defined when output_mode is 'STRUCTURED_JSON'")
        return self

    @classmethod
    def load_from_file(cls, filepath: str) -> "Union[SkillDesign, WorkflowDesign]":
        return load_design_from_file(filepath)


class WorkflowDesign(BaseModel):
    """複数モジュールを連結するワークフローの設計仕様定義。"""
    rationale: str = Field(..., description="設計の思考プロセス。要件の難易度・必要な手順を詳細に分析し、複数のステップ（既存スキル・カスタム関数・自律エージェントのパイプライン接続）が必要であると判定した設計根拠を記述してください。")
    name: str = Field(..., description="ワークフローの名前。小文字のハイフン区切り")
    description: str = Field(..., description="ワークフローの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="ワークフローの仕様概要")
    module_type: Literal[ModuleType.WORKFLOW] = Field(ModuleType.WORKFLOW, description="モジュールの役割分類。ワークフローは必ず 'workflow'")
    functions: list[FunctionDefinition] = Field(..., description="ワークフローパッケージが提供する公開関数の定義リスト。1つ以上の関数定義を含める必要があります")
    dependencies: list[str] = Field([], description="依存するターゲットスキル名のリスト")
    constraints: list[str] = Field([], description="全体の実行に関する制約")
    steps: list[Step] = Field(..., description="ワークフローを構成するステップの定義リスト（有向グラフ）")

    @classmethod
    def load_from_file(cls, filepath: str) -> "Union[SkillDesign, WorkflowDesign]":
        return load_design_from_file(filepath)


# Discriminated Union による統合定義
ModuleDesign = Annotated[
    Union[SkillDesign, WorkflowDesign],
    Field(discriminator="module_type")
]


def load_design_from_file(filepath: str) -> Union[SkillDesign, WorkflowDesign]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"design.json not found at: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.loads(f.read())
        
    adapter = TypeAdapter(ModuleDesign)
    return adapter.validate_python(data)


class SkillMetadata(BaseModel):
    """レジストリ情報と設計仕様情報をマージした、スキルの統合メタデータ"""
    name: str = Field(..., description="スキル名")
    tier: int = Field(0, description="スキルのTier（0から3）", ge=0, le=3)
    last_tested: str | None = Field(None, description="最後にテストされた時刻")
    module_type: ModuleType = Field(ModuleType.SKILL, description="モジュールの役割分類（'skill' または 'workflow'）")
    execution_type: Literal["tool", "agent"] = Field("tool", description="実行タイプ。'tool' または 'agent'")
    description: str = Field("", description="スキルの目的や説明")
    dependencies: list[str] = Field([], description="依存スキルのリスト")
