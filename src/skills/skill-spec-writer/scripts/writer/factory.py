from .base import BaseSpecWriter
from .tool_writer import ToolSpecWriter
from .agent_writer import AgentSpecWriter
from google.adk.tools import ToolContext

class SpecWriterFactory:
    @staticmethod
    def create(execution_type: str, design_data, source_code_dir: str, tool_context: ToolContext) -> BaseSpecWriter:
        if execution_type == "tool":
            return ToolSpecWriter(design_data, source_code_dir, tool_context)
        elif execution_type == "agent":
            return AgentSpecWriter(design_data, source_code_dir, tool_context)
        else:
            raise ValueError(f"Unknown execution type: {execution_type}")
