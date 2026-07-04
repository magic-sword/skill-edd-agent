import os
import sys
import json
from string import Template
from pydantic import BaseModel, Field
from .base import BaseSpecWriter

class SkillTextParts(BaseModel):
    mechanical_description: str = Field(..., description="YAMLフロントマター用の1文の簡潔な要約。機械（LLM）のコンテキストを汚染しない短いもの。")
    human_overview: str = Field(..., description="## 概要 セクションに記述する、人間向けの詳細な機能や動作説明。")
    output_mode: str = Field(..., description="ビジネスロジックに合致する Output Mode。VALUE_ONLY, CONVERSATIONAL, STRUCTURED_JSON のいずれか。")
    output_mode_description: str = Field(..., description="選択された Output Mode に応じた具体的な応答形式の指示説明。")
    trigger_conditions: list[str] = Field(..., description="スキルがトリガーされるプロンプトや表現の具体例（箇条書き用）")

class SkillSpecWriter(BaseSpecWriter):
    def get_pydantic_schema(self):
        return SkillTextParts

    def build_prompt(self, prompt_tmpl: str) -> str:
        # パラメータや依存関係の情報を渡す
        parameters_json = json.dumps(self.design_data.get("parameters", []), indent=2, ensure_ascii=False)
        dependencies_json = json.dumps(self.design_data.get("dependencies", []), indent=2, ensure_ascii=False)
        
        return prompt_tmpl.format(
            target_type="skill",
            name=self.name,
            parameters_json=parameters_json,
            dependencies_json=dependencies_json,
            implementation_code=self.source_code
        )

    def render_markdown(self, text_parts: SkillTextParts) -> str:
        # パラメータテーブルの作成
        param_table = ["| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
        parameters = self.design_data.get("parameters", [])
        for param in parameters:
            req = "はい" if param.get("required", False) else "いいえ"
            param_table.append(f"| {param.get('name')} | {param.get('type')} | {req} | {param.get('description')} |")
            
        params_str = "\n".join(param_table)
        
        # トリガー条件の箇条書き
        triggers = "\n".join([f"- {cond}" for cond in text_parts.trigger_conditions])
        
        # テンプレートファイルのロード
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl_path = os.path.join(script_dir, "..", "assets", "skill_spec.md.template")
        
        with open(tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
            
        t = Template(tmpl_content)
        
        # スクリプトモジュール名（source_code_pathがあればそのbasename、なければデフォルト）
        if self.source_code_path:
            script_file = os.path.basename(self.source_code_path)
            script_module_name, _ = os.path.splitext(script_file)
        else:
            script_module_name = self.name.replace("-", "_")
        
        return t.substitute(
            workflow_name=self.name,
            mechanical_description=text_parts.mechanical_description,
            human_overview=text_parts.human_overview,
            trigger_conditions=triggers,
            output_mode=text_parts.output_mode,
            output_mode_description=text_parts.output_mode_description,
            script_module_name=script_module_name,
            input_parameters=params_str
        )
