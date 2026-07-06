from google.adk.tools import ToolContext
from .models import Input, Output
from .executor import SkillExecutor

SKILL_METADATA = {
    "name": "trigger-evaluator",
    "description": "対象スキルの仕様書（SKILL.md）を静的に具体性と明確性の観点から評価し、トリガー評価用のポジティブ・ネガティブテストケースを自動生成・保存するスキル。",
    "summary": "SKILL.mdを静的評価し、トリガー評価用のテストケースを自動生成・保存するスキル。",
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
