from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState
from edd_agent_tools import merge_result_to_state

def run_design_workflow_step(tool_context: ToolContext) -> str:
    state = SkillsState()
    module = state.get_skill("workflow-designer").load_module()
    
    res = module.workflow_designer(
        prompt=tool_context.state.get("prompt"),
        output_dir=tool_context.state.get("output_dir"),
        target_entry=tool_context.state.get("target_entry")
    )
    return merge_result_to_state(tool_context, res)

def run_create_workflow_step(tool_context: ToolContext) -> str:
    return run_design_workflow_step(tool_context)

def run_update_workflow_step(tool_context: ToolContext) -> str:
    return run_design_workflow_step(tool_context)
