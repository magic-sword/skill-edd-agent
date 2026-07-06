from .base import BaseSpecWriter
from .tool_writer import ToolSpecWriter
from .agent_writer import AgentSpecWriter
from .workflow_writer import WorkflowSpecWriter
from google.adk.tools import ToolContext

class SpecWriterFactory:
    @staticmethod
    def create(design_data, source_code_dir: str, tool_context: ToolContext, prompt: str | None = None) -> BaseSpecWriter:
        from edd_agent_tools.models import ModuleType
        if design_data.module_type == ModuleType.WORKFLOW:
            return WorkflowSpecWriter(design_data, source_code_dir, tool_context, prompt)

        execution_type = getattr(design_data, "execution_type", "tool")
        if execution_type == "tool":
            return ToolSpecWriter(design_data, source_code_dir, tool_context, prompt)
        elif execution_type == "agent":
            return AgentSpecWriter(design_data, source_code_dir, tool_context, prompt)
        else:
            raise ValueError(f"Unknown execution type: {execution_type}")
