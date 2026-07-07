from google.adk.tools import ToolContext
from edd_agent_tools import WorkflowRunner
from .models import Input, Output
from .workflow import root_workflow

SKILL_METADATA = {
    "name": "first-test-runner",
    "description": "指定されたスキルに対して一連のテストと検証を実行し、すべて成功した場合はスキルをTier 1として登録します。",
    "summary": "このワークフローは、対象スキルに対してトリガー評価、テスト実行、インポート検証、設計検証を行います。すべての検証が成功した場合、対象スキルをTier 1（READ_ONLY）としてSkillsStateに登録します。いずれかの検証が失敗した場合は、登録を行わず、失敗の詳細を返します。",
    "execution_type": "agent",
    "output_mode": "STRUCTURED_JSON",
    "dependencies": [
        "trigger-evaluator",
        "test-executor",
        "import-validator",
        "design-validator"
    ]
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # 共通ランナーを直接使用してワークフローを駆動
    runner = WorkflowRunner(
        workflow_name=SKILL_METADATA["name"],
        root_workflow=root_workflow,
        tool_context=tool_context
    )
    result_dict = runner.run(params)
    result = Output(**result_dict)
    if isinstance(result, Output):
        if SKILL_METADATA.get("output_mode") in ("VALUE_ONLY", "CONVERSATIONAL"):
            return result.value
        return result.model_dump_json(by_alias=True)
    return str(result)
