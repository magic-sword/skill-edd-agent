from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
import json

state = SkillsState()
state.load()
skill_designer_module = state.get_skill("skill-designer").load_module()

def run_design_skill_step(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    params = skill_designer_module.Input(
        prompt=tool_context.state.get("prompt"),
        summary=tool_context.state.get("summary"),
        output_dir=tool_context.state.get("output_dir"),
        skill=tool_context.state.get("skill"),
        source_code_dir=tool_context.state.get("source_code_dir")
    )
    res_str = skill_designer_module.process_message(params, tool_context)
    try:
        res_data = json.loads(res_str)
        tool_context.state.update(res_data)
    except Exception:
        pass
    return res_str
