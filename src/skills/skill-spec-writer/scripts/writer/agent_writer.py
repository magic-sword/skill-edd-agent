import os
import json
from pydantic import Field
from .base import BaseSpecWriter, BaseSkillTextParts

class AgentSkillTextParts(BaseSkillTextParts):
    workflow_steps: list[str] = Field(..., description="このスキルが呼び出されたときにエージェント（LLM）が辿る具体的な推論思考プロセスや処理ステップのリスト。")

class AgentSpecWriter(BaseSpecWriter):
    def __init__(self, design_data, source_code_dir: str, tool_context, prompt: str | None = None):
        super().__init__(design_data, source_code_dir, tool_context, prompt)

    def get_pydantic_schema(self):
        return AgentSkillTextParts

    def build_prompt(self, prompt_tmpl: str) -> str:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        specific_prompt_path = os.path.join(script_dir, "..", "assets", "prompt_agent.txt")
        
        with open(specific_prompt_path, "r", encoding="utf-8") as f:
            specific_tmpl = f.read()

        # 共通プロンプトテンプレートのプレースホルダーを展開
        full_tmpl = prompt_tmpl.format(
            name=self.name,
            parameters_json=json.dumps([p.model_dump() for p in self.design_data.parameters], indent=2, ensure_ascii=False),
            dependencies_json=json.dumps(self.design_data.dependencies, indent=2, ensure_ascii=False),
            type_specific_instruction=specific_tmpl
        )
        return full_tmpl

    def _build_execution_instructions(self, required_params: list[str]) -> str:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        inst_path = os.path.join(script_dir, "..", "assets", "execution_instructions_agent.txt")
        with open(inst_path, "r", encoding="utf-8") as f:
            return f.read()
