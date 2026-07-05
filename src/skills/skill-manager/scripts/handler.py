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

def process_message(params: Input, tool_context: ToolContext) -> str:
    # 既存のビジネスロジックを実行
    return run_manager_logic(params, tool_context)
