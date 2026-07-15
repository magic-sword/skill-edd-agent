from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state
import json

state = SkillsState()
state.load()
skill_spec_writer_module = state.get_skill("skill-spec-writer").load_module()

def run_write_spec_step(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    res = skill_spec_writer_module.skill_spec_writer(
        design_path=tool_context.state.get("design_path"),
        skill=tool_context.state.get("skill"),
        output_dir=tool_context.state.get("output_dir"),
        source_code_dir=tool_context.state.get("source_code_dir"),
        prompt=tool_context.state.get("prompt")
    )
    return merge_result_to_state(tool_context, res)
