from google.adk.tools import ToolContext
from .models import Input
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "skill-coder",
    "description": "設計定義ファイル(design.json)と機能要件(prompt)に基づき、ADK 2.0規約およびオブジェクト指向設計に準拠したスキル実装コード(scripts/handler.py, scripts/logic.py等)を自動生成・更新するスキル",
    "execution_type": "tool",
    "output_mode": "STRUCTURED_JSON",
    "dependencies": []
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
