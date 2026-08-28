from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state

def run_contract_test(tool_context: ToolContext) -> str:
    state = SkillsState()
    module = state.get_skill("test-executor").load_module()
    
    skill_name = tool_context.state.get("skill_name") or tool_context.state.get("skill")
    eval_set_path = tool_context.state.get("contract_eval_set_path") or tool_context.state.get("eval_set_path")

    res = module.execute_adk_simulation(
        skill=skill_name,
        eval_set_path=eval_set_path,
        test_type="contract",
        threshold_accuracy=1.0
    )
    status = "success" if getattr(res, "status", None) == "success" or getattr(res, "accuracy", 0.0) >= 1.0 else "failed"
    tool_context.state["contract_test_status"] = status
    return merge_result_to_state(tool_context, res)
