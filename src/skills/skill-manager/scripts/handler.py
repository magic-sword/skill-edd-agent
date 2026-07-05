from google.adk.tools import ToolContext
from .models import Input
from .manage_skills import manage_skills_logic as run_manager_logic

SKILL_METADATA = {
    "name": "skill-manager",
    "description": "スキルのTierおよびメタデータを一括管理・登録します。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # 既存のビジネスロジックを実行
    return run_manager_logic(params, tool_context)
