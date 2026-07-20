from google.adk.tools import ToolContext
from google.adk import Event
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state

def run_route_requirement_step(tool_context: ToolContext) -> Event:
    """
    要件プロンプトを分析し、単体スキルかワークフローかを決定する分岐ルーティングノード。
    """
    state = SkillsState()
    module = state.get_skill("developer-router").load_module()
    
    import os
    
    # もし新規開発で skill が None、かつ output_dir が指定されている場合、
    # output_dir のベースディレクトリ名をターゲット名として設定する。
    if not tool_context.state.get("skill") and tool_context.state.get("output_dir"):
        target_name = os.path.basename(tool_context.state.get("output_dir"))
        tool_context.state["skill"] = target_name
        print(f"DEBUG route_requirement: resolved fallback skill/workflow name = {target_name}")

    print("DEBUG route_requirement: initial state skill =", tool_context.state.get("skill"))
    print("DEBUG route_requirement: initial state prompt =", tool_context.state.get("prompt"))
    print("DEBUG route_requirement: initial state output_dir =", tool_context.state.get("output_dir"))
    res = module.developer_router(
        prompt=tool_context.state.get("prompt")
    )
    
    # 状態にマージする (これで route, rationale, recommended_dependencies が state に入る)
    merge_result_to_state(tool_context, res)
    
    # route を Event に設定して返し、次のエッジ選択の分岐キーにする
    return Event(route=res.route)
