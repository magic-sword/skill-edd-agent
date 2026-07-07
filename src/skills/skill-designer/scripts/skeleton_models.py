from pydantic import BaseModel, Field
from edd_agent_tools.models import ModuleType, StepType, Parameter
from typing import Literal, Union, Annotated

class SkeletonStep(BaseModel):
    name: str = Field(..., description="ステップの識別子名")
    type: StepType = Field(..., description="ステップの種別。'skill' (既存スキル), 'function' (カスタムPython関数), 'agent' (自律エージェント)")
    target: str | None = Field(None, description="typeが 'skill' の場合に呼び出す既存のスキル名")
    description: str | None = Field(None, description="ステップの役割・処理要件を記述する説明")

class WorkflowSkeletonDesign(BaseModel):
    rationale: str = Field(..., description="設計の思考プロセス。")
    name: str = Field(..., description="ワークフローの名前。小文字のハイフン区切り")
    description: str = Field(..., description="ワークフローの目的や役割を記述した簡潔の説明")
    summary: str | None = Field(None, description="仕様概要")
    module_type: Literal[ModuleType.WORKFLOW] = Field(ModuleType.WORKFLOW, description="モジュールの役割分類。ワークフローは必ず 'workflow'")
    parameters: list[Parameter] = Field(..., description="入力パラメータのリスト")
    dependencies: list[str] = Field([], description="依存スキルのリスト")
    constraints: list[str] = Field([], description="全体の実行に関する制約")
    response_parameters: list[Parameter] | None = Field(None, description="全体の出力JSONの構造定義")
    steps: list[SkeletonStep] = Field(..., description="ワークフローを構成するステップの定義リスト")

SkeletonDesign = Annotated[
    Union[WorkflowSkeletonDesign],  # 骨組み設計は常に workflow 構造を想定
    Field(discriminator="module_type")
]
