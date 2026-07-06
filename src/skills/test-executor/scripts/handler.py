from google.adk.tools import ToolContext
from .models import Input, Output
from .executor import SkillExecutor

SKILL_METADATA = {
    "name": "test-executor",
    "description": "ADK評価シミュレーションを実行し、指定されたスキルの動作を検証するためのテスト実行スキルです。評価対象スキル、テストデータセット、合格基準などを指定して、スキルの精度と信頼性を確認できます。",
    "summary": "指定されたスキルに対してADK評価シミュレーションを実行し、その結果を検証します。",
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
