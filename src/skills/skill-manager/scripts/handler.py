from pydantic import BaseModel, Field
from google.adk.tools import ToolContext
from .manage_skills import manage_skills_logic as run_manager_logic

SKILL_METADATA = {
    "name": "skill-manager",
    "description": "スキルのTierおよびメタデータを一括管理・登録します。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

class Input(BaseModel):
    command: str = Field(..., description="実行するコマンド ('register', 'get-tier', 'set-tier', 'list', 'update-meta')")
    skill: str | None = Field(None, description="対象のスキル名")
    tier: int | None = Field(None, description="設定するTier (0, 1, 2, 3)")
    registry_path: str | None = Field(None, description="レジストリファイルのカスタムパス")

def process_message(tool_context: ToolContext):
    # バリデーション済みのオブジェクトを取得
    params: Input = tool_context.state.get("validated_input")
    
    # ロジックが期待するStateを設定
    tool_context.state["command"] = params.command
    tool_context.state["skill"] = params.skill
    tool_context.state["tier"] = params.tier
    tool_context.state["registry_path"] = params.registry_path
    
    # 既存のビジネスロジックを実行
    run_manager_logic(tool_context)
