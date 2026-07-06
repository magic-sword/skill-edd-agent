from google.adk.tools import ToolContext
from .models import Input, Output
from .executor import SkillExecutor

SKILL_METADATA = {
    "name": "design-validator",
    "description": "指定されたスキルの設計仕様（design.json）と生成されたソースコード（models.py, handler.py, executor.py）を読み込み、Gemini API を用いて仕様と実装の整合性を検証するスキルです。",
    "summary": "スキル設計と実装の整合性をGemini APIで検証し、結果を構造化JSONで返却します。",
    "execution_type": "agent",
    "output_mode": "STRUCTURED_JSON",
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
