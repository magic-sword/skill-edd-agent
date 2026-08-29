from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from ..skill_state_client import SkillStateClient

def register_tier2(tool_context: ToolContext) -> str:
    """
    全てのテストが成功した場合に、対象スキルを Tier 2 として登録します。
    """
    overall_status = tool_context.state.get("overall_status", "failed")
    if overall_status != "success":
        msg = "前のテストステップが失敗したため、Tier 2 昇格登録をスキップします。"
        tool_context.state.set("tier2_registration_status", "skipped")
        return msg

    skill_name = tool_context.state.get("skill_name") or tool_context.state.get("skill")
    if not skill_name:
        msg = "Error: スキル名が指定されていません。"
        tool_context.state.set("tier2_registration_status", "failed")
        tool_context.state.set("overall_status", "failed")
        return msg

    try:
        skills_state = SkillsState()
        skill_obj = skills_state.get_skill(skill_name)
        if not skill_obj:
            raise RuntimeError(f"スキル '{skill_name}' が SkillsState に見つかりません。")

        client = SkillStateClient(skills_state=skills_state)
        client.register_skill_as_tier2(skill_obj)

        msg = f"スキル '{skill_name}' が Tier 2 として正常に登録されました。"
        tool_context.state.set("tier2_registration_status", "success")
        tool_context.state.set("overall_status", "success")
        return msg
    except Exception as e:
        msg = f"Tier 2 登録中にエラーが発生しました: {str(e)}"
        tool_context.state.set("tier2_registration_status", "failed")
        tool_context.state.set("overall_status", "failed")
        return msg