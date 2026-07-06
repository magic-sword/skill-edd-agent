from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, model_validator

from typing import Any, get_origin, get_args, Union
from pydantic import BaseModel, create_model

def _clean_type_annotation(anno: Any) -> Any:
    """型アノテーションを再帰的に解析し、内包される Pydantic モデルをクレンジング済みのモデルに置換します。"""
    if anno is None:
        return None

    # 直接 Pydantic モデルの場合 (例: Input)
    if isinstance(anno, type) and issubclass(anno, BaseModel):
        return clean_pydantic_schema(anno)

    # ジェネリック型 (例: list[BaseModel], Union[BaseModel, None] など) の場合
    origin = get_origin(anno)
    if origin is not None:
        args = get_args(anno)
        # 型引数をそれぞれ再帰的にクレンジング
        cleaned_args = tuple(_clean_type_annotation(arg) for arg in args)

        # Union の特殊な再構築
        if origin is Union:
            return Union[cleaned_args]

        try:
            # 引数の数に応じて型を再構成 (list[T] や dict[K, V] 等)
            if len(cleaned_args) == 1:
                return origin[cleaned_args[0]]
            else:
                return origin[cleaned_args]
        except Exception:
            return anno

    return anno

def clean_pydantic_schema(original_model: type[BaseModel]) -> type[BaseModel]:
    """Pydanticモデル定義から、Gemini APIが拒否するカスタムメタデータを除去したクローンモデルを返します（再帰適用）。"""
    fields_definition = {}

    for field_name, field_info in original_model.model_fields.items():
        clean_extra = None
        if isinstance(field_info.json_schema_extra, dict):
            clean_extra = {
                k: v for k, v in field_info.json_schema_extra.items()
                if k not in ["is_prompt_parameter", "prompt_instructions", "prompt_constraints"]
            }

        cleaned_annotation = _clean_type_annotation(field_info.annotation)

        fields_definition[field_name] = (
            cleaned_annotation,
            Field(
                default=field_info.default,
                default_factory=field_info.default_factory,
                description=field_info.description,
                json_schema_extra=clean_extra
            )
        )

    return create_model(
        f"GeminiAPI_{original_model.__name__}",
        **fields_definition
    )

def PromptField(
    default=...,
    description: str = "",
    instructions: str = "",
    constraints: str = "",
    **kwargs
):
    """LLMへの直接の指示（プロンプト）として機能する特別なパラメータを定義するためのフィールドラッパー。

    Args:
        default: デフォルト値。
        description: パラメータの詳細説明。
        instructions: パラメータの有効な指定可能指示ガイドライン。
        constraints: パラメータの構造的な制約ガイドライン。
        **kwargs: 基礎となる Pydantic Field に引き渡す追加 of 属性。

    Returns:
        Pydantic の FieldInfo オブジェクト。
    """
    return Field(
        default,
        description=description,
        json_schema_extra={
            "is_prompt_parameter": True,
            "prompt_instructions": instructions,
            "prompt_constraints": constraints
        },
        **kwargs
    )

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

class SkillDesign(BaseModel):
    """スキルの設計定義を表す Pydantic モデル。

    【設計思想: execution_type による分類の必要性】
    AI エージェント（LLM）が自律的にスキルを発見して実行する際、そのスキルが
    「LLM による自律推論によって実行されるもの（'agent'）」か、
    「決定論的なスクリプトで処理されるもの（'tool'）」かによって、
    仕様書（SKILL.md）の『実行手順（Instructions）』において AI が取るべき行動指針が全く異なります。

    - 'tool': 実際のロジックがスクリプト（Pythonコード等）で完結するため、
             AI 自身がプロンプト等を読み込んで推論したり手動で成果物を組み立てたりする必要はありません。
    - 'agent': スキル内部のプロンプトテンプレート（assets/prompt.txt等）をロードし、
              そこに記載されている指示および思考ステップに従って、AI 自身が推論を実行する必要があります。

    この役割分担とドキュメントの書き分け（指示の出し方）を自動制御するために、この分類が必須となります。
    """
    name: str = Field(..., description="スキルの名前")
    description: str = Field(..., description="スキルの目的や役割を記述した簡潔な説明（L1 description用）")
    summary: str | None = Field(None, description="スキルの仕様概要（ビジネス目的や要求の要約）。仕様書（SKILL.md）の概要セクションにマッピングされます")
    module_type: ModuleType = Field(ModuleType.SKILL, description="モジュールの役割分類（'skill' または 'workflow'）")
    execution_type: Literal["tool", "agent"] = Field(..., description="実行タイプ。'tool' (スクリプト処理) または 'agent' (LLM推論)")
    output_mode: OutputMode = Field(..., description="出力形式（VALUE_ONLY, CONVERSATIONAL, STRUCTURED_JSON）")
    parameters: list[Parameter] = Field(..., description="スキルが受け取るパラメータのリスト")
    dependencies: list[str] = Field([], description="スキルが依存する他のスキルのリスト")
    constraints: list[str] = Field([], description="モデルバリデータ等から抽出された制約条件のリスト")
    response_parameters: list[Parameter] | None = Field(None, description="出力(戻り値)JSONのパラメータ構造定義。STRUCTURED_JSON時に使用されます")

    @model_validator(mode="after")
    def validate_response_parameters(self) -> "SkillDesign":
        if self.output_mode != OutputMode.STRUCTURED_JSON:
            if self.response_parameters:
                raise ValueError("response_parameters can only be defined when output_mode is 'STRUCTURED_JSON'")
        return self

    @classmethod
    def load_from_file(cls, filepath: str) -> "SkillDesign":
        """指定された JSON ファイルを読み込み、SkillDesign スキーマで検証してインスタンスを返します。

        Args:
            filepath: 読み込む設計ファイル（design.json）の絶対パス。

        Returns:
            検証済みの SkillDesign インスタンス。

        Raises:
            FileNotFoundError: 指定されたファイルが存在しない場合。
        """
        import os
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"design.json not found at: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.model_validate_json(f.read())

class RegisteredSkillInfo(BaseModel):
    """レジストリに登録されているスキルまたはエージェントのメタデータ"""
    tier: int = Field(0, description="スキルのTier（0から3）", ge=0, le=3)
    last_tested: str | None = Field(None, description="最後にテストされた時刻（ISO-8601形式）")

class EvalRunResult(BaseModel):
    passed: int = Field(..., description="合格したテストの件数")
    failed: int = Field(..., description="不合格だったテストの件数")
    total: int = Field(..., description="テストの総件数")
    accuracy: float = Field(..., description="テストの合格精度（0.0〜1.0）")
    detail_file_path: str | None = Field(None, description="ADKが生成した詳細結果JSONファイルの絶対パス")


class SkillMetadata(BaseModel):
    """レジストリ情報と設計仕様情報をマージした、スキルの統合メタデータ"""
    name: str = Field(..., description="スキル名")
    tier: int = Field(0, description="スキルのTier（0から3）", ge=0, le=3)
    last_tested: str | None = Field(None, description="最後にテストされた時刻")
    module_type: ModuleType = Field(ModuleType.SKILL, description="モジュールの役割分類（'skill' または 'workflow'）")
    execution_type: Literal["tool", "agent"] = Field("tool", description="実行タイプ。'tool' または 'agent'")
    description: str = Field("", description="スキルの目的や説明")
    dependencies: list[str] = Field([], description="依存スキルのリスト")

