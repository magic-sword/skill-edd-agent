from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState

def run_validate_dependencies_step(tool_context: ToolContext) -> str:
    """
    このワークフローが依存するスキル（test-executor）が適切に解決されているかを検証するカスタム関数。

    Args:
        tool_context: ADKツールコンテキスト。

    Returns:
        処理結果を表現する文字列。
    """
    state = SkillsState()
    
    validation_successful = True
    message = "All required dependencies are successfully resolved."
    try:
        # SkillsState.validate_dependencies() はプロジェクト全体の依存関係を検証する。
        # このワークフローの design.json に記載されている依存関係 (test-executor) が
        # 存在するかを暗黙的にチェックする。
        state.validate_dependencies()
    except Exception as e:
        validation_successful = False
        message = f"Dependency validation failed: {str(e)}"
    
    tool_context.state["dependencies_validation_successful"] = validation_successful
    tool_context.state["dependencies_validation_message"] = message

    return message
