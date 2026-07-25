from google.adk.tools import ToolContext
from google.adk import Event
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state

def run_route_requirement_step(tool_context: ToolContext) -> Event:
    """要件プロンプトを分析し、開発ルート（create_skill, update_skill, create_workflow, update_workflow, proposal）
    を計画決定する分岐ルーティングノード。
    """
    state = SkillsState()
    module = state.get_skill("skill-planner").load_module()

    planner_fn = getattr(module, "skill_planner")
    res = planner_fn(
        prompt=tool_context.state.get("prompt")
    )

    # 状態にマージする (route, target_skill, rationale, recommended_dependencies, proposed_skill)
    merge_result_to_state(tool_context, res)

    # 明示的に target_skill が得られた場合は state['skill'] にも伝播させる
    if getattr(res, "target_skill", None):
        tool_context.state["skill"] = res.target_skill

    # route を Event に設定して返し、次のエッジ選択の分岐キーにする
    return Event(route=res.route)
