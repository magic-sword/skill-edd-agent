import os
import json
from string import Template
from pydantic import BaseModel, Field
from .base import BaseSpecWriter

class SkillTextParts(BaseModel):
    purpose: str = Field(..., description="このスキルの本質的な目的と提供する価値を要約した簡潔な日本語の1〜2文。")
    features: list[str] = Field(..., description="このスキルが提供する具体的な主要機能のリスト。")
    workflow_steps: list[str] = Field(..., description="このスキルが呼び出されたときにエージェント（LLM）が辿る具体的な推論思考プロセスや処理ステップのリスト。")
    trigger_conditions: list[str] = Field(..., description="スキルがトリガーされるプロンプトや表現の具体例（箇条書き用）")

class AgentSpecWriter(BaseSpecWriter):
    def __init__(self, design_data, source_code_dir: str, tool_context):
        super().__init__(design_data, source_code_dir, tool_context)

    def get_pydantic_schema(self):
        return SkillTextParts

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

    def render_markdown(self, text_parts: SkillTextParts) -> str:
        # 決定論的な概要（Overview）の組み立て
        overview_lines = [
            text_parts.purpose,
            "\n### 主な機能",
            "\n".join([f"* {f}" for f in text_parts.features]),
            "\n### 内部処理の流れ",
            "\n".join([f"{i+1}. {step}" for i, step in enumerate(text_parts.workflow_steps)])
        ]
        overview_str = "\n".join(overview_lines)

        # パラメータテーブルの作成
        param_table = ["| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
        for param in self.design_data.parameters:
            req = "はい" if param.required else "いいえ"
            param_table.append(f"| {param.name} | {param.type} | {req} | {param.description} |")
            
        params_str = "\n".join(param_table)
        triggers = "\n".join([f"- {cond}" for cond in text_parts.trigger_conditions])
        
        # 決定論的な説明文の構築
        out_mode = self.design_data.output_mode
        if out_mode == "VALUE_ONLY":
            out_mode_desc = "出力は単純なプレーンテキストの値のみとなります。"
        elif out_mode == "CONVERSATIONAL":
            out_mode_desc = "ユーザーとの対話を継続する会話形式の応答を出力します。"
        else: # STRUCTURED_JSON
            out_mode_desc = "特定のJSONスキーマ構造に厳密に従った構造化データを出力します。生成結果のパース成功時に生成されたファイルのパスや、エラー時にはエラーメッセージと詳細情報が含まれます。"

        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # execution_instructions_agent.txt をロード
        inst_path = os.path.join(script_dir, "..", "assets", "execution_instructions_agent.txt")
        with open(inst_path, "r", encoding="utf-8") as f:
            exec_instructions = f.read()

        # テンプレートのロード
        tmpl_path = os.path.join(script_dir, "..", "assets", "skill_spec.md.template")
        with open(tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
            
        t = Template(tmpl_content)
        
        # 制約事項のレンダリング
        constraints_section = ""
        if self.design_data.constraints:
            lines = ["### 制約事項\n"]
            for constraint in self.design_data.constraints:
                lines.append(f"- {constraint}")
            constraints_section = "\n".join(lines)
        
        return t.substitute(
            skill_name=self.name,
            mechanical_description=self.design_data.description,
            human_overview=overview_str,
            trigger_conditions=triggers,
            execution_instructions=exec_instructions,
            output_mode=out_mode,
            output_mode_description=out_mode_desc,
            input_parameters=params_str,
            constraints_section=constraints_section
        )
