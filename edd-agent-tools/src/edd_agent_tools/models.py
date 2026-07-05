from enum import StrEnum
from pydantic import BaseModel, Field, model_validator

class OutputMode(StrEnum):
    VALUE_ONLY = "VALUE_ONLY"
    CONVERSATIONAL = "CONVERSATIONAL"
    STRUCTURED_JSON = "STRUCTURED_JSON"


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

class SkillDesign(BaseModel):
    """
    スキルの設計定義を表すPydanticモデル。
    
    【設計思想: execution_typeによる分類の必要性】
    AIエージェント（LLM）が自律的にスキルを発見して実行する際、そのスキルが
    「LLMによる自律推論によって実行されるもの（'agent'）」か、
    「決定論的なスクリプトで処理されるもの（'tool'）」かによって、
    仕様書（SKILL.md）の『実行手順（Instructions）』においてAIが取るべき行動指針が全く異なります。
    
    - 'tool': 実際のロジックがスクリプト（Pythonコード等）で完結するため、
             AI自身がプロンプト等を読み込んで推論したり手動で成果物を組み立てたりする必要はありません。
    - 'agent': スキル内部のプロンプトテンプレート（assets/prompt.txt等）をロードし、
              そこに記載されている指示および思考ステップに従って、AI自身が推論を実行する必要があります。
              
    この役割分担とドキュメントの書き分け（指示の出し方）を自動制御するために、この分類が必須となります。
    """
    name: str = Field(..., description="スキルの名前")
    description: str = Field(..., description="スキルの目的や役割を記述した簡潔な説明（L1 description用）")
    execution_type: str = Field(..., description="実行タイプ。'tool' (スクリプト処理) または 'agent' (LLM推論)")
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
        """
        指定された JSON ファイルを読み込み、SkillDesign スキーマで検証してインスタンスを返します。
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

