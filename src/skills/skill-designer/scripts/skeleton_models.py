from pydantic import BaseModel, Field
from edd_agent_tools import ModuleType, Parameter
from typing import Literal

class SkeletonDesign(BaseModel):
    rationale: str = Field(..., description="設計の思考プロセス。どのような機能要件があり、なぜこのパラメータ設計や制約を定めたかの理由。")
    name: str = Field(..., description="モジュールの名前。小文字のハイフン区切り")
    description: str = Field(..., description="モジュールの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="仕様概要")
    module_type: Literal[ModuleType.SKILL] = Field(ModuleType.SKILL, description="モジュールの種類。アトミックな1機能は必ず 'skill'")
    parameters: list[Parameter] = Field(..., description="入力パラメータのリスト")
    dependencies: list[str] = Field([], description="依存スキルのリスト")
    constraints: list[str] = Field([], description="全体の実行に関する制約")
    response_parameters: list[Parameter] | None = Field(None, description="全体の出力JSONの構造定義")


