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
        # パラメータや依存関係の情報を渡す (Pydantic 属性から JSON 化)
        parameters_dict = [p.model_dump() for p in self.design_data.parameters]
        parameters_json = json.dumps(parameters_dict, indent=2, ensure_ascii=False)
        dependencies_json = json.dumps(self.design_data.dependencies, indent=2, ensure_ascii=False)
        
        return prompt_tmpl.format(
            target_type="workflow",
            name=self.name,
            parameters_json=parameters_json,
            dependencies_json=dependencies_json,
            implementation_code=self.source_code
        )

    def render_markdown(self, text_parts: WorkflowTextParts) -> str:
        # パラメータテーブルの作成 (Pydantic 属性アクセス)
        param_table = ["| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
        for param in self.design_data.parameters:
            req = "はい" if param.required else "いいえ"
            param_table.append(f"| {param.name} | {param.type} | {req} | {param.description} |")
            
        params_str = "\n".join(param_table)
        
        # dependencies のクレンジング (Pydantic から取得)
        dependencies = self.design_data.dependencies

        # dependencies の YAML リスト
        dependencies_yaml = "\n".join([f"  - {dep}" for dep in dependencies])
        
        # 実行コマンドの引数例の組み立て
        args_list = []
        for param in self.design_data.parameters:
            args_list.append(f"  --{param.name} \"<{param.description}>\" \\")
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
