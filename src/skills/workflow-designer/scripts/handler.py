from google.adk.tools import ToolContext
from .models import WorkflowDesignerOutput
from .executor import SkillExecutor

def workflow_designer(
    prompt: str,
    summary: str = None,
    output_dir: str = None,
    target_entry: str = "workflow",
    tool_context: ToolContext = None
) -> WorkflowDesignerOutput:
    """ワークフロー要件に基づいて新しいワークフローを設計します。

    Args:
        prompt: 設計するワークフローの機能要件やフローの追加要望を記述した自然言語のテキスト。
        summary: ワークフローの仕様概要。指定した場合、自動要約より優先して design.json に反映されます。
        output_dir: 生成されたdesign.jsonを保存するディレクトリのパス。
        target_entry: 優先する論理配置先エントリー名。
        tool_context: ADKのToolContextインスタンス。

    Returns:
        処理結果オブジェクト (WorkflowDesignerOutput)。
    """
    executor = SkillExecutor()
    return executor.workflow_designer(
        prompt=prompt,
        summary=summary,
        output_dir=output_dir,
        target_entry=target_entry
    )
