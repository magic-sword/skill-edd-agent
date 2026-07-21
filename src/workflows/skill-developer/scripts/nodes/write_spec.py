from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state
import json

def run_write_spec_step(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    state = SkillsState()
    module = state.get_skill("skill-spec-writer").load_module()
    
    res = module.generate_skill_spec(
        prompt=tool_context.state.get("prompt"),
        skill=tool_context.state.get("skill"),
        design_path=tool_context.state.get("design_path"),
        output_dir=tool_context.state.get("output_dir"),
        source_code_dir=tool_context.state.get("source_code_dir")
    )
    return merge_result_to_state(tool_context, res)
