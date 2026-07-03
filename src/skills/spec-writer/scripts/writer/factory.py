from .base import BaseSpecWriter
from .skill_writer import SkillSpecWriter
from .workflow_writer import WorkflowSpecWriter
from google.adk.tools import ToolContext

class SpecWriterFactory:
    @staticmethod
    def create(target_type: str, name: str, design_data: dict, source_code: str, tool_context: ToolContext) -> BaseSpecWriter:
        if target_type == "skill":
            return SkillSpecWriter(name, design_data, source_code, tool_context)
        elif target_type == "workflow":
            return WorkflowSpecWriter(name, design_data, source_code, tool_context)
        else:
            raise ValueError(f"Unknown target type: {target_type}")
