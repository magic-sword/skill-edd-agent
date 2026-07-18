import os
from abc import abstractmethod
from string import Template
from pydantic import BaseModel, Field
from .base import BaseSpecWriter

class BaseSkillTextParts(BaseModel):
    features: list[str] = Field(..., description="このスキルが提供する具体的な主要機能のリスト。")
    trigger_conditions: list[str] = Field(..., description="スキルがトリガーされるプロンプトや表現の具体例（箇条書き用）")

class BaseSkillSpecWriter(BaseSpecWriter):
    """
    シングル・マルチを問わず、functions を持つ「スキル型モジュール」の共通仕様書（README）生成ライター。
    """
    def render_markdown(self, text_parts) -> str:
        # 決定論的な概要（Overview）の組み立て
        features_list_str = "\n".join([f"* {f}" for f in text_parts.features])
        steps_list_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(text_parts.workflow_steps)])

        overview_tmpl = self._load_template("overview_details.md.template")
        overview_str = Template(overview_tmpl).safe_substitute(
            features=features_list_str,
            workflow_steps=steps_list_str
        )

        # 各公開関数（APIエンドポイント）の情報をカプセル化して構築
        functions_sections = []
        for fn in self.design_data.functions:
            # 関数固有の必要な引数リストを作成して build_execution_instructions に渡す
            fn_req_params = [f"`{p.name}`" for p in fn.parameters if p.required]
            if not fn_req_params:
                # 必須引数がない場合は、その関数のパラメータから最大2つをフォールバックとして渡す
                fn_req_params = [f"`{p.name}`" for p in fn.parameters[:2]]
            fn_exec_inst = self._build_execution_instructions(fn_req_params)

            # 入力パラメータテーブル
            input_table = [self._load_template("param_table_header_skill.md.template").strip()]
            row_tmpl = self._load_template("param_table_row_skill.md.template").replace("\n", "").strip()
            for param in fn.parameters:
                req = "はい" if param.required else "いいえ"
                formatted_type = self._format_parameter_type(param)
                formatted_desc = self._format_parameter_description(param)
                default_val = f"`{param.default}`" if param.default is not None else "-"
                input_table.append(Template(row_tmpl).safe_substitute(
                    name=param.name,
                    type=formatted_type,
                    required=req,
                    default=default_val,
                    description=formatted_desc
                ))
            input_parameters_str = "\n".join(input_table)

            # プロンプトパラメータのガイドライン (対象関数内にある場合のみ挿入)
            prompt_guide_str = ""
            guide_tmpl = self._load_template("prompt_guide.md.template")
            for param in fn.parameters:
                if getattr(param, "is_prompt_parameter", None):
                    inst = getattr(param, "prompt_instructions", None) or "指示トーンや特別に盛り込んでほしい仕様コンテキストの指定。"
                    cons = getattr(param, "prompt_constraints", None) or "出力ドキュメント全体のレイアウト構成・見出し等の構造変更は不可。"
                    prompt_guide_str = "\n" + Template(guide_tmpl).safe_substitute(
                        name=param.name,
                        instructions=inst,
                        constraints=cons
                    )

            # 出力仕様
            out_mode = getattr(self.design_data, "output_mode", "STRUCTURED_JSON")
            if out_mode == "STRUCTURED_JSON":
                if fn.response_parameters:
                    output_table = [self._load_template("param_table_header.md.template").strip()]
                    row_tmpl = self._load_template("param_table_row.md.template").replace("\n", "").strip()
                    for param in fn.response_parameters:
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
                else:
                    output_params_str = "出力パラメータは定義されていません。"

                output_spec_tmpl = self._load_template("output_spec_structured.md.template")
                output_spec_str = Template(output_spec_tmpl).safe_substitute(
                    output_parameters=output_params_str
                )
            else:
                mode_label = "プレーンテキスト（値のみ）" if out_mode == "VALUE_ONLY" else "会話形式応答"
                resp_type = getattr(fn, "response_type", None) or "str"
                explanation = "スキル実行結果を示す単一のテキストメッセージが返されます。" if out_mode == "VALUE_ONLY" else "ユーザーへの返答メッセージが返されます。"

                output_spec_tmpl = self._load_template("output_spec_plain.md.template")
                output_spec_str = Template(output_spec_tmpl).safe_substitute(
                    output_mode=out_mode,
                    output_mode_label=mode_label,
                    response_type=resp_type,
                    output_mode_explanation=explanation
                )

            func_section_tmpl = self._load_template("function_section.md.template")
            func_str = Template(func_section_tmpl).safe_substitute(
                func_name=fn.name,
                func_description=fn.description,
                exec_instructions=fn_exec_inst.strip(),
                input_parameters=input_parameters_str,
                prompt_guide=prompt_guide_str,
                output_spec=output_spec_str.strip()
            )
            functions_sections.append(func_str)

        functions_str = "\n\n---\n\n".join(functions_sections)
        triggers = "\n".join([f"- {cond}" for cond in text_parts.trigger_conditions])

        # テンプレートのロード
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

        # 概要には、design.jsonのsummary (無ければ description) をマウントする
        mechanical_summary = getattr(self.design_data, "summary", None) or self.design_data.description
        yaml_safe_description = self.design_data.description.replace("\n", " ").replace("\"", "\\\"")

        return t.substitute(
            skill_name=self.name,
            mechanical_description=mechanical_summary,
            yaml_safe_description=yaml_safe_description,
            overview_details=overview_str,
            trigger_conditions=triggers,
            functions_section=functions_str,
            constraints_section=constraints_section
        )
