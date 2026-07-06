from google.adk.tools import ToolContext
from .models import Input, Output
from .executor import SkillExecutor

SKILL_METADATA = {
    "name": "eval-unit-tester",
    "description": "対象スキルに対して評価用の単体テストスイートを自動生成します。",
    "summary": "指定されたスキルに対する単体テストケースと評価設定ファイルを自動生成するツール。",
    "execution_type": "tool",
    "output_mode": "VALUE_ONLY",
    "dependencies": []
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ビジネスロジックを呼び出す
    executor = SkillExecutor(params, tool_context)
    result = executor.execute()
    if isinstance(result, Output):
        if SKILL_METADATA.get("output_mode") in ("VALUE_ONLY", "CONVERSATIONAL"):
            return result.value
        return result.model_dump_json(by_alias=True)
    return str(result)
