from pydantic import BaseModel, Field

class Parameter(BaseModel):
    name: str = Field(..., description="パラメータの名前")
    type: str = Field(..., description="パラメータの型（例: 'str', 'int', 'bool', 'list'）")
    description: str = Field(..., description="パラメータの説明")
    required: bool = Field(False, description="このパラメータが必須かどうか")
    default: str | None = Field(None, description="パラメータのデフォルト値（任意、文字列等として表現）")

class SkillDesign(BaseModel):
    name: str = Field(..., description="スキルの名前")
    description: str = Field(..., description="スキルの目的や役割を記述した簡潔な説明（L1 description用）")
    execution_type: str = Field(..., description="実行タイプ。'tool' (スクリプト処理) または 'agent' (LLM推論)")
    output_mode: str = Field(..., description="出力形式（VALUE_ONLY, CONVERSATIONAL, STRUCTURED_JSON）")
    parameters: list[Parameter] = Field(..., description="スキルが受け取るパラメータのリスト")
    dependencies: list[str] = Field([], description="スキルが依存する他のスキルのリスト")
