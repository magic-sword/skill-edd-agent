from .base import BaseSpecWriter
from .tool_writer import ToolSpecWriter
from .agent_writer import AgentSpecWriter
from .workflow_writer import WorkflowSpecWriter
class SpecWriterFactory:
    @staticmethod
    def create(design_data, source_code_dir: str, prompt: str | None = None) -> BaseSpecWriter:
        from edd_agent_tools import ModuleType
        if design_data.module_type == ModuleType.WORKFLOW:
            return WorkflowSpecWriter(design_data, source_code_dir, prompt)

        execution_type = getattr(design_data, "execution_type", "tool")
        if execution_type == "tool":
            return ToolSpecWriter(design_data, source_code_dir, prompt)
        elif execution_type == "agent":
            return AgentSpecWriter(design_data, source_code_dir, prompt)
        else:
            raise ValueError(f"Unknown execution type: {execution_type}")
