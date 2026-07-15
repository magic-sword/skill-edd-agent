from pydantic import BaseModel, Field
from edd_agent_tools import ModuleType, StepType, Parameter
from typing import Literal, Union, Annotated

class SkeletonStep(BaseModel):
    name: str = Field(..., description="ステップの識別子名")
    type: StepType = Field(..., description="ステップの種別。'skill' (既存スキル), 'function' (カスタムPython関数), 'agent' (自律エージェント)")
    target: str | None = Field(None, description="typeが 'skill' の場合に呼び出す既存のスキル名")
    description: str | None = Field(None, description="ステップの役割・処理要件を記述する説明")

class SkeletonDesign(BaseModel):
    rationale: str = Field(..., description="設計の思考プロセス。なぜこの module_type (skill または workflow) を選択したのかの理由。")
    name: str = Field(..., description="モジュールの名前。小文字のハイフン区切り")
    description: str = Field(..., description="モジュールの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="仕様概要")
    module_type: ModuleType = Field(ModuleType.SKILL, description="モジュールの種類。アトミックな1機能は 'skill'、他の複数スキルを連携・調整する場合は 'workflow'")
    parameters: list[Parameter] = Field(..., description="入力パラメータのリスト")
    dependencies: list[str] = Field([], description="依存スキルのリスト")
    constraints: list[str] = Field([], description="全体の実行に関する制約")
    response_parameters: list[Parameter] | None = Field(None, description="全体の出力JSONの構造定義")
    steps: list[SkeletonStep] = Field([], description="workflow の場合のみ指定するステップ定義リスト。skill の場合は空リストにしてください。")


