from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .develop_skill import develop_skill_logic as run_developer_logic

SKILL_METADATA = {
    "name": "skill-developer",
    "description": "指定された要件（prompt）に基づき、SkillDeveloperAgentを起動して新規スキルを自動開発・設計・実装するワークフロー。",
    "execution_type": "workflow",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    skill: str = Field(..., description="開発対象のスキル名")
    prompt: str = Field(..., description="開発するスキルの機能要件")

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # ロジックが期待するStateを設定
    tool_context.state["skill"] = params.skill
    tool_context.state["prompt"] = params.prompt
    
    # 既存のビジネスロジックを実行
    run_developer_logic(tool_context)
