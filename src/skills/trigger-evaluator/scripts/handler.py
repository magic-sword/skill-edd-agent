from google.adk.tools import ToolContext
from .models import Input
from .logic import process_message as run_logic

SKILL_METADATA = {
    "name": "trigger-evaluator",
    "description": "設計情報（Pydanticスキーマ等）を動的にロードし、トリガー精度の静的評価およびテスト生成を行います。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
