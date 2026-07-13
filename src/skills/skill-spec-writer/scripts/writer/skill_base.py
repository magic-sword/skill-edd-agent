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

        # パラメータテーブルおよび出力パラメータテーブルの作成
        # functions 配下の各関数を処理する
        param_sections = []
        output_sections = []
        required_params = []

        for fn in self.design_data.functions:
            # 入力パラメータテーブル
            param_sections.append(f"### 入力パラメータ ({fn.name})\n")
            param_table = ["| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
            for param in fn.parameters:
                req = "はい" if param.required else "いいえ"
                formatted_type = self._format_parameter_type(param)
                formatted_desc = self._format_parameter_description(param)
                param_table.append(f"| {param.name} | {formatted_type} | {req} | {formatted_desc} |")
                if param.required:
                    required_params.append(f"`{param.name}` (関数 `{fn.name}`)")
            param_sections.append("\n".join(param_table))

            # 出力パラメータテーブル (STRUCTURED_JSON時のみ)
            if self.design_data.output_mode == "STRUCTURED_JSON" and fn.response_parameters:
                output_sections.append(f"### 出力パラメータ (構造化JSONの戻り値構造) ({fn.name})\n")
                output_table = ["| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
                for param in fn.response_parameters:
                    req = "はい" if param.required else "いいえ"
                    formatted_type = self._format_parameter_type(param)
                    formatted_desc = self._format_parameter_description(param)
                    output_table.append(f"| {param.name} | {formatted_type} | {req} | {formatted_desc} |")
                output_sections.append("\n".join(output_table))

        params_str = "\n\n".join(param_sections)
        
        if output_sections:
            output_params_section = "\n\n".join(output_sections)
        else:
            out_mode = getattr(self.design_data, "output_mode", "STRUCTURED_JSON")
            if out_mode == "VALUE_ONLY":
                output_params_section = "### 出力値\n\nスキル実行結果を示す単一のテキストメッセージ（プレーンテキスト）が返されます。"
            elif out_mode == "CONVERSATIONAL":
                output_params_section = "### 出力値\n\nユーザーへの返答メッセージ（プレーンテキスト）が返されます。"
            else:
                output_params_section = ""

        triggers = "\n".join([f"- {cond}" for cond in text_parts.trigger_conditions])

        # 決定論的な説明文の構築
        out_mode = getattr(self.design_data, "output_mode", "STRUCTURED_JSON")
        if out_mode == "VALUE_ONLY":
            out_mode_desc = "出力は単純なプレーンテキストの値のみとなります。"
        elif out_mode == "CONVERSATIONAL":
            out_mode_desc = "ユーザーとの対話を継続する会話形式の応答を出力します。"
        else:  # STRUCTURED_JSON
            out_mode_desc = "特定のJSONスキーマ構造に厳密に従った構造化データを出力します。生成結果のパース成功時に生成されたファイルのパスや、エラー時にはエラーメッセージと詳細情報が含まれます。"

        # 各具象クラス固有の instructions 構築
        exec_instructions = self._build_execution_instructions(required_params)

        # design.json 内に prompt_parameter メタデータが存在する場合、
        # プロンプトパラメータの有効指示と制約ガイドを決定論的にマージする
        prompt_guides = []
        for fn in self.design_data.functions:
            for param in fn.parameters:
                if getattr(param, "is_prompt_parameter", None):
                    inst = getattr(param, "prompt_instructions", None) or "指示トーンや特別に盛り込んでほしい仕様コンテキストの指定。"
                    cons = getattr(param, "prompt_constraints", None) or "出力ドキュメント全体のレイアウト構成・見出し等の構造変更は不可。"
                    prompt_guides.append(
                        f"\n> [!NOTE]\n"
                        f"> **`{param.name}` パラメータの使用ガイドライン (関数 `{fn.name}`):**\n"
                        f"> * **指定可能な指示**: {inst}\n"
                        f"> * **構造的な制約（指定不可）**: {cons}\n"
                    )

        if prompt_guides:
            exec_instructions = f"{exec_instructions.strip()}\n" + "\n".join(prompt_guides)

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
            execution_instructions=exec_instructions,
            output_mode=out_mode,
            output_mode_description=out_mode_desc,
            input_parameters=params_str,
            output_parameters_section=output_params_section,
            constraints_section=constraints_section
        )
