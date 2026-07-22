from typing import Literal, Any
from pydantic import BaseModel, Field
from edd_agent_tools import ModuleType, StepType

class SkeletonStep(BaseModel):
    name: str = Field(..., description="ステップの識別子名")
    type: StepType = Field(..., description="ステップの種別。'skill' (既存スキル), 'function' (カスタムPython関数), 'agent' (自律エージェント)")
    target: str | None = Field(None, description="typeが 'skill' の場合に呼び出す既存のスキル名。'function' や 'agent' の場合は None にしてください。")
    description: str | None = Field(None, description="ステップの役割・処理要件を記述する説明")

class ControlFlowNode(BaseModel):
    target: str | None = Field(None, description="呼び出す既存スキル名または関数の識別名")
    next: str | None = Field(None, description="次に実行する単一ステップ名。分岐がない場合に指定。")
    transitions: dict[str, str] | None = Field(None, description="条件分岐における分岐先マッピング。例: {'skill': 'design-skill', 'workflow': 'design-workflow'}")

class ControlFlow(BaseModel):
    start: str = Field(..., description="ワークフローの開始ステップ名")
    nodes: dict[str, ControlFlowNode] = Field(..., description="各ステップ名をキーとする制御フローノードの定義辞書")

class ExpectedToolUse(BaseModel):
    name: str = Field(..., description="呼び出される期待ツールの名前。")
    args: dict[str, Any] = Field(default_factory=dict, description="ツール呼び出しに渡される期待パラメータ辞書。")

class EvalScenario(BaseModel):
    scenario_id: str = Field(..., description="評価シナリオの一意なID。例: 'single_skill_creation'")
    description: str = Field(..., description="シナリオの説明・想定ユースケース。")
    input: dict[str, Any] = Field(..., description="シナリオ実行時の入力引数・プロンプト辞書。")
    expected_trajectory: list[ExpectedToolUse] = Field(default_factory=list, description="本シナリオで期待されるツール呼び出し経路の正解シーケンス。")
    expected_final_status: str = Field("success", description="シナリオ完了時に期待される最終ステータス。例: 'success', 'failed', 'halted'")

class SkeletonDesign(BaseModel):
    rationale: str = Field(..., description="設計の思考プロセス。どのような要件があり、なぜこのステップ群（有向グラフ）を構成したかの設計根拠。")
    name: str = Field(..., description="ワークフローの名前。小文字のハイフン区切り")
    description: str = Field(..., description="ワークフローの目的や役割を記述した簡潔な説明")
    summary: str | None = Field(None, description="仕様概要")
    module_type: Literal[ModuleType.WORKFLOW] = Field(ModuleType.WORKFLOW, description="モジュールの種類。ワークフローは必ず 'workflow'")
    dependencies: list[str] = Field([], description="依存するターゲットスキル名のリスト")
    constraints: list[str] = Field([], description="全体の実行に関する制約")
    steps: list[SkeletonStep] = Field(..., description="ワークフローを構成するステップの定義リスト")
    control_flow: ControlFlow | None = Field(None, description="ワークフローの制御フロー構造定義（ノード遷移と分岐関係）")
    eval_scenarios: list[EvalScenario] = Field([], description="経路評価およびゴールデンテスト用の代表的シナリオ定義リスト")

