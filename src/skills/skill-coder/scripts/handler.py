from google.adk.tools import ToolContext
from .models import Input, Output
from .executor import SkillExecutor

SKILL_METADATA = {
    "name": "skill-coder",
    "description": "設計定義ファイル(design.json)と機能要件(prompt)に基づき、ADK 2.0規約およびオブジェクト指向設計に準拠したスキル実装コードを自動生成・更新するスキル。",
    "summary": "設計定義ファイル(design.json)と機能要件(prompt)に基づき、ADK 2.0規約およびオブジェクト指向設計に準拠したスキル実装コードを自動生成・更新するスキル。",
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
