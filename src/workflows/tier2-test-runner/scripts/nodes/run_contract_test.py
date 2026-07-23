from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state
import json

def run_contract_test(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    state = SkillsState()
    module = state.get_skill("test-executor").load_module()
    
    res = module.execute_adk_simulation(
        skill=tool_context.state.get("skill"),
        eval_set_path=tool_context.state.get("eval_set_path"),
        test_type=tool_context.state.get("test_type"),
        threshold_accuracy=tool_context.state.get("threshold_accuracy")
    )
    return merge_result_to_state(tool_context, res)
