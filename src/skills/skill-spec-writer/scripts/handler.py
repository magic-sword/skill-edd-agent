from google.adk.tools import ToolContext
from .models import Input, Output
from .executor import SkillExecutor

SKILL_METADATA = {
    "name": "skill-spec-writer",
    "description": "設計情報（Pydanticスキーマ等）を動的にロードし、ADK 2.0仕様に準拠したSKILL.mdを生成します。",
    "summary": "既存のスキル設計情報（design.json）を基に、ADK 2.0に準拠したSKILL.md仕様書を自動生成します。これにより、開発者はドキュメント作成の手間を省き、常に最新かつ正確なスキル仕様書を維持できます。",
    "execution_type": "tool",
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
