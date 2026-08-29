from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state

def run_golden_test(tool_context: ToolContext) -> str:
    state = SkillsState()
    module = state.get_skill("golden-test-executor").load_module()
    
    skill_name = tool_context.state.get("skill_name") or tool_context.state.get("skill")
    eval_set_path = tool_context.state.get("golden_eval_set_path") or tool_context.state.get("eval_set_path")

    res = module.run_tests(
        skill_name=skill_name,
        eval_set_path=eval_set_path,
        env=tool_context.state.get("env", "sandbox")
    )
    status = "success" if getattr(res, "accuracy", 0.0) >= 0.8 or getattr(res, "passed", 0) > 0 else "failed"
    tool_context.state["golden_test_status"] = status
    return merge_result_to_state(tool_context, res)
