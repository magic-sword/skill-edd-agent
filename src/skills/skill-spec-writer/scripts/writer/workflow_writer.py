import os
from string import Template
from .base import BaseSpecWriter
from pydantic import BaseModel, Field

class WorkflowTextParts(BaseModel):
    purpose: str = Field(..., description="このワークフローの本質的な目的と提供するビジネス上の価値。")
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

        prompt = (
            f"{prompt_tmpl}\n\n"
            f"=== ワークフロー設計書 (Workflow Design) ===\n"
            f"名称: {self.name}\n"
            f"説明: {self.design_data.description}\n"
            f"制約事項: {self.design_data.constraints}\n"
            f"構成ステップ:\n{steps_str}\n"
            "上記の情報から、ワークフローの『ビジネス上の価値(purpose)』、『主要な特徴・機能(features)』、『起動トリガーの具体例(trigger_conditions)』、および『各ステップの連携手順(workflow_steps)』を考察・抽出し、指定された JSON スキーマに従って返却してください。"
        )
        return prompt

    def _build_execution_instructions(self, required_params: list[str]) -> str:
        steps_str = "\n".join([f"1. **{step.name}** ({step.type}): {step.description or step.target or ''}" for step in self.design_data.steps])
        inst = (
            "このワークフローは、複数の処理ノードをパイプラインで実行する自律接続システムです。\n"
            f"以下の順番でステップが接続・順次実行されます：\n\n{steps_str}\n\n"
            "引数パラメータが入力されると、STARTノードから順に状態（tool_context.state）を伝播しながら処理が進みます。"
        )
        return inst

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

        # パラメータテーブルの作成
        param_table = ["| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
        required_params = []
        for param in self.design_data.parameters:
            req = "はい" if param.required else "いいえ"
            formatted_type = self._format_parameter_type(param)
            formatted_desc = self._format_parameter_description(param)
            param_table.append(f"| {param.name} | {formatted_type} | {req} | {formatted_desc} |")
            if param.required:
                required_params.append(f"`{param.name}`")
            
        params_str = "\n".join(param_table)
        triggers = "\n".join([f"- {cond}" for cond in text_parts.trigger_conditions])
        
        # 出力パラメータテーブルの作成
        output_params_section = ""
        if getattr(self.design_data, "response_parameters", None):
            output_table = ["### 出力パラメータ (構造化JSONの戻り値構造)\n", "| パラメータ名 | 型 | 必須 | 説明 |", "|---|---|---|---|"]
            for param in self.design_data.response_parameters:
                req = "はい" if param.required else "いいえ"
                formatted_type = self._format_parameter_type(param)
                formatted_desc = self._format_parameter_description(param)
                output_table.append(f"| {param.name} | {formatted_type} | {req} | {formatted_desc} |")
            output_params_section = "\n".join(output_table)
        else:
            # 構造化JSON以外の場合に、出力値のプレーンテキスト仕様を明記する
            out_mode = getattr(self.design_data, "output_mode", "STRUCTURED_JSON")
            if out_mode == "VALUE_ONLY":
                output_params_section = "### 出力値\n\nスキル実行結果を示す単一のテキストメッセージ（プレーンテキスト）が返されます。"
            elif out_mode == "CONVERSATIONAL":
                output_params_section = "### 出力値\n\nユーザーへの返答メッセージ（プレーンテキスト）が返されます。"
        
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
        for param in self.design_data.parameters:
            if getattr(param, "is_prompt_parameter", None):
                inst = getattr(param, "prompt_instructions", None) or "指示トーンや特別に盛り込んでほしい仕様コンテキストの指定。"
                cons = getattr(param, "prompt_constraints", None) or "出力ドキュメント全体のレイアウト構成・見出し等の構造変更は不可。"
                prompt_guides.append(
                    f"\n> [!NOTE]\n"
                    f"> **`{param.name}` パラメータの使用ガイドライン:**\n"
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
