from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state
import json

def run_code_skill_step(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    state = SkillsState()
    module = state.get_skill("skill-coder").load_module()
    
    res = module.skill_coder(
        prompt=tool_context.state.get("prompt"),
        skill=tool_context.state.get("skill"),
        design_path=tool_context.state.get("design_path"),
        output_dir=tool_context.state.get("output_dir")
    )
    return merge_result_to_state(tool_context, res)
