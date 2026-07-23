from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state
import json

def run_golden_test(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    state = SkillsState()
    module = state.get_skill("golden-test-executor").load_module()
    
    res = module.run_tests(
        skill_name=tool_context.state.get("skill_name"),
        eval_set_path=tool_context.state.get("eval_set_path"),
        env=tool_context.state.get("env")
    )
    return merge_result_to_state(tool_context, res)
