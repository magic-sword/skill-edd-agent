from google.adk.tools import ToolContext
from google.adk import Event
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state

def run_route_requirement_step(tool_context: ToolContext) -> Event:
    """
    要件プロンプトを分析し、単体スキル、ワークフロー、または事前スキル提案かを計画決定する分岐ルーティングノード。
    """
    state = SkillsState()
    module = state.get_skill("skill-planner").load_module()

    planner_fn = getattr(module, "skill_planner", getattr(module, "developer_router", None))
    res = planner_fn(
        prompt=tool_context.state.get("prompt")
    )

    # 状態にマージする (これで route, rationale, recommended_dependencies, proposed_skill が state に入る)
    merge_result_to_state(tool_context, res)

    # route を Event に設定して返し、次のエッジ選択の分岐キーにする
    return Event(route=res.route)
