from google.adk.tools import ToolContext
from .models import Input
from .generate_skill import process_message as run_logic

SKILL_METADATA = {
    "name": "skill-generator",
    "description": "ADKサブエージェントを動的に起動し、指定された要件に基づいてスキルコードを自律生成します。",
    "execution_type": "agent",
    "output_mode": "CONVERSATIONAL",
    "dependencies": []
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    return run_logic(params, tool_context)
