from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json

state = SkillsState()
state.load()
skill_coder_module = state.get_skill("skill-coder").load_module()

def run_code_skill_step(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    params = skill_coder_module.Input(
        prompt=tool_context.state.get("prompt"),
        skill=tool_context.state.get("skill"),
        design_path=tool_context.state.get("design_path"),
        output_dir=tool_context.state.get("output_dir")
    )
    res_str = skill_coder_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str
