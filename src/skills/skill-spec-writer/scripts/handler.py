from google.adk.tools import ToolContext
from .models import Input, Output
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "skill-spec-writer",
    "description": "設計情報（Pydanticスキーマ等）を動的にロードし、ADK 2.0仕様に準拠したSKILL.mdを生成します。",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON",
    "dependencies": []
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    result = run_logic(params, tool_context)
    # result が Output インスタンスであることを想定して model_dump_json を呼び出す
    return result.model_dump_json(by_alias=True)
