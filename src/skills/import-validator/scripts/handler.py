from google.adk.tools import ToolContext
from .models import Input, Output
from .executor import SkillExecutor

SKILL_METADATA = {
    "name": "import-validator",
    "description": "指定されたスキルを動的にインポートし、その成否を検証します。",
    "summary": "このスキルは、ADK 2.0のSkillsStateメカニズムを使用して、指定されたスキルモジュール（scripts/__init__.py）を動的にロードできるかを検証します。動的ロードに成功した場合は成功ステータスを、失敗した場合は失敗ステータスと詳細なエラー情報（トレースバック）を構造化されたJSON形式で返却します。これにより、スキルがADK 2.0の規約に準拠し、正しくロード可能であるかを確認できます。",
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
