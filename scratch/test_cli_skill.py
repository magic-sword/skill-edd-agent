import json
from google.adk.tools import ToolContext
from edd_agent_tools.testing.cli import run_skill_as_cli

def process_message(tool_context: ToolContext):
    user_message = tool_context.state.get("user_message", "")
    tool_context.state["result_message"] = f"Processed: {user_message}"

if __name__ == "__main__":
    run_skill_as_cli(process_message)
