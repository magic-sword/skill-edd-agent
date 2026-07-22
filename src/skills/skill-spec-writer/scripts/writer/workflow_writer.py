import os
from string import Template
from .base import BaseSpecWriter
from pydantic import BaseModel, Field

class WorkflowTextParts(BaseModel):
    features: list[str] = Field(..., description="このワークフローが提供する具体的な主要機能のリスト。")
    trigger_conditions: list[str] = Field(..., description="ワークフローがトリガーされるプロンプトや表現の具体例（箇条書き用）")
    workflow_steps: list[str] = Field(..., description="各ステップ（ノード）の処理概要、順序、および役割の説明。")

class WorkflowSpecWriter(BaseSpecWriter):
    """
    ワークフロー型モジュールのための仕様書（README）生成ライター。
    """
    def get_pydantic_schema(self):
        return WorkflowTextParts

    def build_prompt(self, prompt_tmpl: str) -> str:
        steps_str = ""
        for step in self.design_data.steps:
            steps_str += f"- ステップ名: {step.name} (型: {step.type})\n"
            if step.target:
                steps_str += f"  ターゲット: {step.target}\n"
            if step.description:
                steps_str += f"  処理要件: {step.description}\n"

        control_flow_str = ""
        control_flow = getattr(self.design_data, "control_flow", None)
        if control_flow:
            if isinstance(control_flow, dict):
                control_flow_str = f"制御フロー (control_flow):\n{control_flow}\n"
            elif hasattr(control_flow, "model_dump"):
                control_flow_str = f"制御フロー (control_flow):\n{control_flow.model_dump()}\n"

        prompt_workflow_asset = self._load_asset("prompt_workflow.txt")
        design_block_tmpl = self._load_asset("prompt_workflow_design_block.txt")

        design_block_str = Template(design_block_tmpl).safe_substitute(
            name=self.name,
            description=self.design_data.description,
            constraints=self.design_data.constraints,
            steps_str=steps_str,
            control_flow_str=control_flow_str
        )

        prompt = f"{prompt_tmpl}\n\n{prompt_workflow_asset}\n\n{design_block_str}"
        return prompt

    def _build_execution_instructions(self, required_params: list[str]) -> str:
        steps_str = "\n".join([f"1. **{step.name}** ({step.type}): {step.description or step.target or ''}" for step in self.design_data.steps])
        control_flow = getattr(self.design_data, "control_flow", None)
        flow_note = "動的分岐" if control_flow and (getattr(control_flow, "nodes", None) or (isinstance(control_flow, dict) and "nodes" in control_flow)) else "順次実行"
        
        exec_tmpl = self._load_asset("execution_instructions_workflow.txt")
        inst = Template(exec_tmpl).safe_substitute(
            flow_note=flow_note,
            steps_str=steps_str
        )
        return inst

    def render_markdown(self, text_parts) -> str:
        # 決定論的な概要（Overview）の組み立て
        features_list_str = "\n".join([f"* {f}" for f in text_parts.features])
        steps_list_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(text_parts.workflow_steps)])

        overview_tmpl = self._load_template("overview_details.md.template")
        overview_str = Template(overview_tmpl).safe_substitute(
            features=features_list_str,
            workflow_steps=steps_list_str
        )

        # パラメータテーブルの作成
        param_table = [self._load_template("param_table_header.md.template").strip()]
        required_params = []
        if getattr(self.design_data, "module_type", None) == "workflow":
            target_params = getattr(self.design_data, "parameters", [])
        else:
            target_params = self.design_data.functions[0].parameters
        
        row_tmpl = self._load_template("param_table_row.md.template").replace("\n", "").strip()
        for param in target_params:
            req = "はい" if param.required else "いいえ"
            formatted_type = self._format_parameter_type(param)
            formatted_desc = self._format_parameter_description(param)
            param_table.append(Template(row_tmpl).safe_substitute(
                name=param.name,
                type=formatted_type,
                required=req,
                description=formatted_desc
            ))
            if param.required:
                required_params.append(f"`{param.name}`")
            
        params_str = "\n".join(param_table)
        triggers = "\n".join([f"- {cond}" for cond in text_parts.trigger_conditions])
        
        # 出力パラメータテーブルの作成
        output_params_section = ""
        if getattr(self.design_data, "module_type", None) == "workflow":
            target_response_params = getattr(self.design_data, "response_parameters", [])
        else:
            target_response_params = self.design_data.functions[0].response_parameters

        if target_response_params:
            output_table = [self._load_template("param_table_header.md.template").strip()]
            row_tmpl = self._load_template("param_table_row.md.template").replace("\n", "").strip()
            for param in target_response_params:
                req = "はい" if param.required else "いいえ"
                formatted_type = self._format_parameter_type(param)
                formatted_desc = self._format_parameter_description(param)
                output_table.append(Template(row_tmpl).safe_substitute(
                    name=param.name,
                    type=formatted_type,
                    required=req,
                    description=formatted_desc
                ))
            output_params_str = "\n".join(output_table)

            output_spec_tmpl = self._load_template("output_spec_structured_workflow.md.template")
            output_params_section = Template(output_spec_tmpl).safe_substitute(
                output_parameters=output_params_str
            )
        else:
            # 構造化JSON以外の場合に、出力値のプレーンテキスト仕様を明記する
            out_mode = getattr(self.design_data, "output_mode", "STRUCTURED_JSON")
            if out_mode in ("VALUE_ONLY", "CONVERSATIONAL"):
                output_params_section = self._load_template("output_plain_text.md.template")
        
        # 決定論的な説明文の構築
        out_mode = getattr(self.design_data, "output_mode", "STRUCTURED_JSON")
        if out_mode == "VALUE_ONLY":
            out_mode_desc = "出力は単純なプレーンテキストの値のみとなります。"
        elif out_mode == "CONVERSATIONAL":
            out_mode_desc = "ユーザーとの対話を継続する会話形式の応答を出力します。"
        else: # STRUCTURED_JSON
            out_mode_desc = "特定のJSONスキーマ構造に厳密に従った構造化データを出力します。生成結果のパース成功時に生成されたファイルのパスや、エラー時にはエラーメッセージと詳細情報が含まれます。"

        # 各具象クラス固有の instructions 構築
        exec_instructions = self._build_execution_instructions(required_params)

        # design.json 内に prompt_parameter メタデータが存在する場合、
        # プロンプトパラメータの有効指示と制約ガイドを決定論的にマージする
        prompt_guides = []
        guide_tmpl = self._load_template("prompt_guide.md.template")
        for param in target_params:
            if getattr(param, "is_prompt_parameter", None):
                inst = getattr(param, "prompt_instructions", None) or "指示トーンや特別に盛り込んでほしい仕様コンテキストの指定。"
                cons = getattr(param, "prompt_constraints", None) or "出力ドキュメント全体のレイアウト構成・見出し等の構造変更は不可。"
                prompt_guides.append(Template(guide_tmpl).safe_substitute(
                    name=param.name,
                    instructions=inst,
                    constraints=cons
                ))

        if prompt_guides:
            exec_instructions = f"{exec_instructions.strip()}\n" + "\n".join(prompt_guides)

        # テンプレートのロード
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl_path = os.path.join(script_dir, "..", "assets", "workflow_spec.md.template")
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
        
        # 概要には、design.jsonのsummary (無ければ description) をマウントする
        mechanical_summary = getattr(self.design_data, "summary", None) or self.design_data.description
        yaml_safe_description = self.design_data.description.replace("\n", " ").replace("\"", "\\\"")

        return t.substitute(
            skill_name=self.name,
            mechanical_description=mechanical_summary,
            yaml_safe_description=yaml_safe_description,
            overview_details=overview_str,
            trigger_conditions=triggers,
            execution_instructions=exec_instructions,
            output_mode=out_mode,
            output_mode_description=out_mode_desc,
            input_parameters=params_str,
            output_parameters_section=output_params_section,
            constraints_section=constraints_section
        )
