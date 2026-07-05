import os
import json
from string import Template
from pydantic import BaseModel, Field
from .base import BaseSpecWriter

class SkillTextParts(BaseModel):
    human_overview: str = Field(..., description="## 概要 セクションに記述する、人間向けの詳細な機能や動作説明。")
    trigger_conditions: list[str] = Field(..., description="スキルがトリガーされるプロンプトや表現の具体例（箇条書き用）")

class ToolSpecWriter(BaseSpecWriter):
    def __init__(self, design_data, source_code_dir: str, tool_context):
        super().__init__(design_data, source_code_dir, tool_context)

    def get_pydantic_schema(self):
        return SkillTextParts

    def build_prompt(self, prompt_tmpl: str) -> str:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        specific_prompt_path = os.path.join(script_dir, "..", "assets", "prompt_tool.txt")
        
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
        # パラメータテーブルの作成
        param_table = ["| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
        required_params = []
        for param in self.design_data.parameters:
            req = "はい" if param.required else "いいえ"
            param_table.append(f"| {param.name} | {param.type} | {req} | {param.description} |")
            if param.required:
                required_params.append(f"`{param.name}`")
            
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
        
        # execution_instructions_tool.txt をロードして展開
        inst_path = os.path.join(script_dir, "..", "assets", "execution_instructions_tool.txt")
        with open(inst_path, "r", encoding="utf-8") as f:
            inst_tmpl = f.read()
        param_list_str = ", ".join(required_params) if required_params else "パラメータ"
        exec_instructions = Template(inst_tmpl).substitute(param_list=param_list_str)

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
            human_overview=text_parts.human_overview,
            trigger_conditions=triggers,
            execution_instructions=exec_instructions,
            output_mode=out_mode,
            output_mode_description=out_mode_desc,
            input_parameters=params_str,
            constraints_section=constraints_section
        )
