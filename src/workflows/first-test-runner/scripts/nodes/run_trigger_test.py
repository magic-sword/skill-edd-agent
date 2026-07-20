from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state
import json

def run_run_trigger_test_step(tool_context: ToolContext) -> str:
    # 設計書の inputs マッピングから直接決定論的に引数を抽出
    state = SkillsState()
    module = state.get_skill("test-executor").load_module()
    
    import os
    skill_name = tool_context.state.get("skill_name")
    base_path = tool_context.state.get("eval_set_base_path")
    eval_file = os.path.join(base_path, f"{skill_name.replace('-', '_')}_trigger.evalset.json")
    
    res = module.execute_adk_simulation(
        skill=skill_name,
        eval_set_path=eval_file,
        test_type="trigger",
        threshold_accuracy=0.9
    )
    print(f"DEBUG run_trigger_test: type(res)={type(res)}, res={res}")
    is_success = False
    if hasattr(res, "status"):
        is_success = (res.status == "success")
    elif isinstance(res, dict):
        is_success = (res.get("status") == "success")
    
    tool_context.state["trigger_test_is_success"] = is_success
    return merge_result_to_state(tool_context, res)
