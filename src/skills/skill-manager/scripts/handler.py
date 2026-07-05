from google.adk.tools import ToolContext
from .models import Input, Output
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "skill-manager",
    "description": "スキルのTierおよびメタデータを一括管理・登録します。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    result = run_logic(params, tool_context)
    if isinstance(result, Output):
        if SKILL_METADATA.get("output_mode") in ("VALUE_ONLY", "CONVERSATIONAL"):
            return result.value
        return result.model_dump_json(by_alias=True)
    return str(result)
