from .base import BaseSpecWriter
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext

class WorkflowTextParts(BaseModel):
    purpose: str = Field(..., description="このワークフローの本質的な目的と提供するビジネス上の価値。")
    features: list[str] = Field(..., description="このワークフローが提供する具体的な主要機能のリスト。")
    trigger_conditions: list[str] = Field(..., description="ワークフローがトリガーされるプロンプトや表現の具体例（箇ため書き用）")
    workflow_steps: list[str] = Field(..., description="各ステップ（ノード）の処理概要、順序、および役割の説明。")

class WorkflowSpecWriter(BaseSpecWriter):
    """
    ワークフロー型モジュールのための仕様書（README）生成ライター。
    """
    def get_pydantic_schema(self):
        return WorkflowTextParts

    def build_prompt(self, prompt_tmpl: str) -> str:
        steps_str = ""
        for step in self.design_data.steps:
            steps_str += f"- ステップ名: {step.name} (型: {step.type})\n"
            if step.target:
                steps_str += f"  ターゲット: {step.target}\n"
            if step.description:
                steps_str += f"  処理要件: {step.description}\n"

        prompt = (
            f"{prompt_tmpl}\n\n"
            f"=== ワークフロー設計書 (Workflow Design) ===\n"
            f"名称: {self.name}\n"
            f"説明: {self.design_data.description}\n"
            f"制約事項: {self.design_data.constraints}\n"
            f"構成ステップ:\n{steps_str}\n"
            "上記の情報から、ワークフローの『ビジネス上の価値(purpose)』、『主要な特徴・機能(features)』、『起動トリガーの具体例(trigger_conditions)』、および『各ステップの連携手順(workflow_steps)』を考察・抽出し、指定された JSON スキーマに従って返却してください。"
        )
        return prompt

    def _build_execution_instructions(self, required_params: list[str]) -> str:
        steps_str = "\n".join([f"1. **{step.name}** ({step.type}): {step.description or step.target or ''}" for step in self.design_data.steps])
        inst = (
            "このワークフローは、複数の処理ノードをパイプラインで実行する自律接続システムです。\n"
            f"以下の順番でステップが接続・順次実行されます：\n\n{steps_str}\n\n"
            "引数パラメータが入力されると、STARTノードから順に状態（tool_context.state）を伝播しながら処理が進みます。"
        )
        return inst
