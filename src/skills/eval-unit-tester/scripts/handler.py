from google.adk.tools import ToolContext
from .models import Input
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "eval-unit-tester",
    "description": "対象スキルに対して評価用の単体テストスイートを自動生成します。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
