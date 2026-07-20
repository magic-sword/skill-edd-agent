from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state
import json

import os

def run_write_spec_step(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    state = SkillsState()
    module = state.get_skill("skill-spec-writer").load_module()
    
    design_path_val = tool_context.state.get("design_path")
    if not design_path_val and tool_context.state.get("output_dir"):
        design_path_val = os.path.join(tool_context.state.get("output_dir"), "assets/design.json")

    res = module.generate_skill_spec(
        prompt=tool_context.state.get("prompt"),
        skill=tool_context.state.get("skill"),
        design_path=design_path_val,
        output_dir=tool_context.state.get("output_dir"),
        source_code_dir=tool_context.state.get("source_code_dir")
    )
    return merge_result_to_state(tool_context, res)
