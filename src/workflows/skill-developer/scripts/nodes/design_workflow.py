from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state
import json

def run_design_workflow_step(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    state = SkillsState()
    module = state.get_skill("workflow-designer").load_module()
    
    res = module.workflow_designer(
        prompt=tool_context.state.get("prompt"),
        output_dir=tool_context.state.get("output_dir"),
        target_entry=tool_context.state.get("target_entry"),
        summary=tool_context.state.get("summary")
    )
    return merge_result_to_state(tool_context, res)
