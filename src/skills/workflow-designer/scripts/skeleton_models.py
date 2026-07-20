from pydantic import BaseModel, Field
from edd_agent_tools import ModuleType, StepType
from typing import Literal

class SkeletonStep(BaseModel):
    name: str = Field(..., description="ステップの識別子名")
    type: StepType = Field(..., description="ステップの種別。'skill' (既存スキル), 'function' (カスタムPython関数), 'agent' (自律エージェント)")
    target: str | None = Field(None, description="typeが 'skill' の場合に呼び出す既存のスキル名。'function' や 'agent' の場合は None にしてください。")
    description: str | None = Field(None, description="ステップの役割・処理要件を記述する説明")

class SkeletonDesign(BaseModel):
    rationale: str = Field(..., description="設計の思考プロセス。どのような要件があり、なぜこのステップ群（有向グラフ）を構成したかの設計根拠。")
    name: str = Field(..., description="ワークフローの名前。小文字のハイフン区切り")
    description: str = Field(..., description="ワークフローの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="仕様概要")
    module_type: Literal[ModuleType.WORKFLOW] = Field(ModuleType.WORKFLOW, description="モジュールの種類。ワークフローは必ず 'workflow'")
    dependencies: list[str] = Field([], description="依存するターゲットスキル名のリスト")
    constraints: list[str] = Field([], description="全体の実行に関する制約")
    steps: list[SkeletonStep] = Field(..., description="ワークフローを構成するステップの定義リスト")
