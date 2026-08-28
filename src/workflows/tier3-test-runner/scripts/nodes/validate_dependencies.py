from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState

def validate_dependencies(tool_context: ToolContext) -> str:
    skills_state = SkillsState()
    skill_name = tool_context.state.get("skill_name") or tool_context.state.get("skill")
    
    try:
        skills_state.validate_dependencies()
        tool_context.state["validation_success"] = True
        return f"Dependency validation for '{skill_name}': Success"
    except Exception as e:
        tool_context.state["validation_success"] = False
        return f"Dependency validation failed: {str(e)}"