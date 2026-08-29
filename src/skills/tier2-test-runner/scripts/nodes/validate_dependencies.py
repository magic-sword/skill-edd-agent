from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState

def validate_dependencies(tool_context: ToolContext) -> str:
    """
    スキルの依存関係を検証し、必要なスキルがすべて利用可能であることを確認します。
    """
    overall_status = "failed" # デフォルトは失敗
    validation_message = ""

    try:
        skills_state = SkillsState()
        # validate_dependencies は ValueError を送出する可能性がある
        skills_state.validate_dependencies()
        overall_status = "success"
        validation_message = "すべての依存関係が正常に検証されました。"
    except ValueError as e:
        validation_message = f"依存関係の検証に失敗しました: {str(e)}"
    except Exception as e:
        validation_message = f"予期せぬエラーが発生しました: {str(e)}"

    tool_context.state.set("dependencies_validated", overall_status == "success")
    tool_context.state.set("validation_message", validation_message)
    tool_context.state.set("overall_status", overall_status) # 全体のステータスを更新

    return validation_message
