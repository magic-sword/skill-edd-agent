from google.adk.tools import ToolContext
from .models import Input, Output
from .workflow_logic import workflow_logic as run_workflow_logic

SKILL_METADATA = {
    "name": "skill-developer",
    "description": "スキルを生成するワークフローエージェント。",
    "summary": "src/skills/skill-designer、src/skills/skill-coder、src/skills/skill-spec-writerを順番に実行し、スキル設計・実装を行うワークフローエージェント。",
    "execution_type": "agent",
    "output_mode": "STRUCTURED_JSON",
    "dependencies": [
        "skill-designer",
        "skill-coder",
        "skill-spec-writer"
    ]
}

def process_message(params: Input, tool_context: ToolContext) -> str:
    # ワークフローを実行するビジネスロジックを呼び出す
    result = run_workflow_logic(params, tool_context)
    return result
