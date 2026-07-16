import os
from abc import abstractmethod
from string import Template
from pydantic import BaseModel, Field
from .base import BaseSpecWriter

class BaseSkillTextParts(BaseModel):
    purpose: str = Field(..., description="このスキルの本質的な目的と提供する価値を要約した簡潔な1〜2文。")
    features: list[str] = Field(..., description="このスキルが提供する具体的な主要機能のリスト。")
    trigger_conditions: list[str] = Field(..., description="スキルがトリガーされるプロンプトや表現の具体例（箇条書き用）")

class BaseSkillSpecWriter(BaseSpecWriter):
    """
    シングル・マルチを問わず、functions を持つ「スキル型モジュール」の共通仕様書（README）生成ライター。
    """
    def render_markdown(self, text_parts) -> str:
        # 決定論的な概要（Overview）の組み立て
        purpose_str = getattr(self.design_data, "summary", None) or text_parts.purpose

        overview_lines = [
            purpose_str,
            "\n### 主な機能",
            "\n".join([f"* {f}" for f in text_parts.features]),
            "\n### 内部処理の流れ",
            "\n".join([f"{i+1}. {step}" for i, step in enumerate(text_parts.workflow_steps)])
        ]
        overview_str = "\n".join(overview_lines)

        # 各公開関数（APIエンドポイント）の情報をカプセル化して構築
        functions_sections = []
        for fn in self.design_data.functions:
            fn_lines = [
                f"### {fn.name}\n",
                f"{fn.description}\n",
                "#### 実行方法\n"
            ]

            # 関数固有の必要な引数リストを作成して build_execution_instructions に渡す
            fn_req_params = [f"`{p.name}`" for p in fn.parameters if p.required]
            if not fn_req_params:
                # 必須引数がない場合は、その関数のパラメータから最大2つをフォールバックとして渡す
                fn_req_params = [f"`{p.name}`" for p in fn.parameters[:2]]
            fn_exec_inst = self._build_execution_instructions(fn_req_params)
            fn_lines.append(f"{fn_exec_inst.strip()}\n")

            # 入力パラメータテーブル
            fn_lines.append("#### 入力パラメータ\n")
            input_table = [
                "| パラメータ名 | 型 | 必須 | デフォルト値 | 説明 |",
                "|---|---|---|---|---|",
            ]
            for param in fn.parameters:
                req = "はい" if param.required else "いいえ"
                formatted_type = self._format_parameter_type(param)
                formatted_desc = self._format_parameter_description(param)
                default_val = f"`{param.default}`" if param.default is not None else "-"
                input_table.append(f"| {param.name} | {formatted_type} | {req} | {default_val} | {formatted_desc} |")
            fn_lines.append("\n".join(input_table) + "\n")

            # プロンプトパラメータのガイドライン (対象関数内にある場合のみ挿入)
            for param in fn.parameters:
                if getattr(param, "is_prompt_parameter", None):
                    inst = getattr(param, "prompt_instructions", None) or "指示トーンや特別に盛り込んでほしい仕様コンテキストの指定。"
                    cons = getattr(param, "prompt_constraints", None) or "出力ドキュメント全体のレイアウト構成・見出し等の構造変更は不可。"
                    fn_lines.append(
                        f"> [!NOTE]\n"
                        f"> **`{param.name}` パラメータの使用ガイドライン:**\n"
                        f"> * **指定可能な指示**: {inst}\n"
                        f"> * **構造的な制約（指定不可）**: {cons}\n"
                    )

            # 出力仕様
            fn_lines.append("#### 出力仕様\n")
            out_mode = getattr(self.design_data, "output_mode", "STRUCTURED_JSON")
            if out_mode == "STRUCTURED_JSON":
                fn_lines.append(f"* **出力モード**: `STRUCTURED_JSON`\n")
                if fn.response_parameters:
                    output_table = [
                        "| パラメータ名 | 型 | 必須 | 説明 |",
                        "|---|---|---|---|",
                    ]
                    for param in fn.response_parameters:
                        req = "はい" if param.required else "いいえ"
                        formatted_type = self._format_parameter_type(param)
                        formatted_desc = self._format_parameter_description(param)
                        output_table.append(f"| {param.name} | {formatted_type} | {req} | {formatted_desc} |")
                    fn_lines.append("\n".join(output_table) + "\n")
                else:
                    fn_lines.append("出力パラメータは定義されていません。\n")
            else:
                mode_label = "プレーンテキスト（値のみ）" if out_mode == "VALUE_ONLY" else "会話形式応答"
                fn_lines.append(f"* **出力モード**: `{out_mode}` ({mode_label})\n")
                resp_type = getattr(fn, "response_type", None) or "str"
                fn_lines.append(f"* **戻り値の型**: `{resp_type}`\n")
                if out_mode == "VALUE_ONLY":
                    fn_lines.append("スキル実行結果を示す単一のテキストメッセージが返されます。\n")
                else:
                    fn_lines.append("ユーザーへの返答メッセージが返されます。\n")

            functions_sections.append("\n".join(fn_lines))

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

        return t.substitute(
            skill_name=self.name,
            mechanical_description=self.design_data.description,
            human_overview=overview_str,
            trigger_conditions=triggers,
            functions_section=functions_str,
            constraints_section=constraints_section
        )
