from google.adk.tools import ToolContext
from .models import Input, Output
from .executor import SkillExecutor

SKILL_METADATA = {
    "name": "skill-designer",
    "description": "スキル設計要件に基づいて新しいスキルを設計し、または既存スキルを再設計するツール。",
    "summary": "自然言語の要件や既存のソースコードを基に、ADK 2.0互換のdesign.jsonを設計・生成します。これにより、新しいスキルの定義や既存スキルの再設計を効率的に行えます。",
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
