from google.adk.tools import ToolContext
from .models import Input, Output
from .workflow_logic import workflow_logic as run_workflow_logic

SKILL_METADATA = {
    "name": "skill-developer",
    "description": "スキルを設計、実装、および仕様書を作成するワークフローエージェント。",
    "summary": "このワークフローは、ユーザーからの要件プロンプトに基づいて、skill-designer、skill-coder、skill-spec-writerの各スキルを順に実行し、新しいスキルを生成します。設計、実装、仕様書作成の一連のプロセスを自動化し、成果物を指定されたディレクトリに出力します。",
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
