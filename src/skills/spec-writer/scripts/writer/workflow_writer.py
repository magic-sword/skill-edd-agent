import os
import sys
import json
from string import Template
from pydantic import BaseModel, Field
from .base import BaseSpecWriter

class WorkflowTextParts(BaseModel):
    mechanical_description: str = Field(..., description="YAMLフロントマター用の1文の簡潔な要約。機械（LLM）のコンテキストを汚染しない短いもの。")
    human_overview: str = Field(..., description="## 概要 セクションに記述する、人間向けの詳細なワークフロー機能や動作説明。")
    dependency_explanations: dict[str, str] = Field(..., description="依存関係セクションにおける、各依存スキルの本ワークフロー内での具体的な役割についての解説。キーは依存スキル名。")

class WorkflowSpecWriter(BaseSpecWriter):
    def get_pydantic_schema(self):
        return WorkflowTextParts

    def build_prompt(self, prompt_tmpl: str) -> str:
        parameters_json = json.dumps(self.design_data.get("parameters", []), indent=2, ensure_ascii=False)
        dependencies_json = json.dumps(self.design_data.get("dependencies", []), indent=2, ensure_ascii=False)
        
        return prompt_tmpl.format(
            target_type="workflow",
            name=self.name,
            parameters_json=parameters_json,
            dependencies_json=dependencies_json,
            implementation_code=self.source_code
        )

    def render_markdown(self, text_parts: WorkflowTextParts) -> str:
        # パラメータテーブルの作成
        param_table = ["| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
        parameters = self.design_data.get("parameters", [])
        for param in parameters:
            req = "はい" if param.get("required", False) else "いいえ"
            desc = param.get("help" if "help" in param else "description", "")
            param_table.append(f"| {param.get('name')} | {param.get('type')} | {req} | {desc} |")
            
        params_str = "\n".join(param_table)
        
        # dependencies のクレンジング（文字列のリストにする）
        dependencies = []
        for dep in self.design_data.get("dependencies", []):
            if isinstance(dep, dict):
                skill_name = dep.get("skill")
                if skill_name:
                    dependencies.append(skill_name)
            elif isinstance(dep, str):
                dependencies.append(dep)

        # dependencies の YAML リスト
        dependencies_yaml = "\n".join([f"  - {dep}" for dep in dependencies])
        
        # 実行コマンドの引数例の組み立て
        args_list = []
        for param in parameters:
            name = param.get("name")
            desc = param.get("help" if "help" in param else "description", "値")
            args_list.append(f"  --{name} \"<{desc}>\" \\")
        # 最後のバックスラッシュを除去
        execution_arguments = "\n".join(args_list).rstrip(" \\")
        
        # 依存スキルの役割解説
        dep_exps = []
        for dep in dependencies:
            exp = text_parts.dependency_explanations.get(dep, "このワークフロー内で使用されます。")
            dep_exps.append(f"- **{dep}**: {exp}")
        dependencies_explanation = "\n".join(dep_exps)
        
        # テンプレートファイルのロード
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl_path = os.path.join(script_dir, "..", "assets", "workflow_spec.md.template")
        
        with open(tmpl_path, "r", encoding="utf-8") as f:
            tmpl_content = f.read()
            
        t = Template(tmpl_content)
        
        return t.substitute(
            workflow_name=self.name,
            mechanical_description=text_parts.mechanical_description,
            dependencies_yaml=dependencies_yaml,
            human_overview=text_parts.human_overview,
            input_parameters=params_str,
            execution_arguments=execution_arguments,
            dependencies_explanation=dependencies_explanation
        )
