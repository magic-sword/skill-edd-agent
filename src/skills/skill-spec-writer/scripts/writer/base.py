import os
import sys
import json
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext

from google import genai
from google.genai import types

from edd_agent_tools.models import SkillDesign
from edd_agent_tools.gemini import GeminiRequest

class BaseSkillTextParts(BaseModel):
    purpose: str = Field(..., description="このスキルの本質的な目的と提供する価値を要約した簡潔な日本語の1〜2文。")
    features: list[str] = Field(..., description="このスキルが提供する具体的な主要機能のリスト。")
    trigger_conditions: list[str] = Field(..., description="スキルがトリガーされるプロンプトや表現の具体例（箇条書き用）")

class BaseSpecWriter(ABC):
    def __init__(self, design_data: SkillDesign, source_code_dir: str, tool_context: ToolContext, prompt: str | None = None):
        self.design_data = design_data
        self.name = design_data.name
        self.source_code_dir = source_code_dir
        self.tool_context = tool_context
        self.prompt = prompt
        
        from edd_agent_tools import GeminiClient
        self.client = GeminiClient()

    def _format_parameter_type(self, param) -> str:
        """Pydanticの型表現に近いわかりやすい型名を返す"""
        if getattr(param, "choices", None):
            choices_expr = ", ".join(repr(c) if isinstance(c, str) else str(c) for c in param.choices)
            return f"Literal[{choices_expr}]"
        
        t_str = param.type.strip().lower()
        if t_str == "list" and getattr(param, "items_type", None):
            return f"list[{param.items_type}]"
            
        return param.type

    def _format_parameter_description(self, param) -> str:
        """説明文に制約情報を付与して返す"""
        constraints = []
        if getattr(param, "ge", None) is not None:
            constraints.append(f"最小値: {param.ge}")
        if getattr(param, "le", None) is not None:
            constraints.append(f"最大値: {param.le}")
        if getattr(param, "pattern", None) is not None:
            constraints.append(f"パターン: `{param.pattern}`")
        if getattr(param, "min_length", None) is not None:
            constraints.append(f"最小長: {param.min_length}")
        if getattr(param, "max_length", None) is not None:
            constraints.append(f"最大長: {param.max_length}")
            
        desc = param.description or ""
        if constraints:
            constraint_str = ", ".join(constraints)
            if desc:
                desc = f"{desc} *(制約: {constraint_str})*"
            else:
                desc = f"*(制約: {constraint_str})*"
        return desc

    @abstractmethod
    def get_pydantic_schema(self):
        """抽出用の Pydantic モデルを返す"""
        pass

    @abstractmethod
    def build_prompt(self, prompt_tmpl: str) -> str:
        """LLM に渡すプロンプトを構築する"""
        pass

    @abstractmethod
    def _build_execution_instructions(self, required_params: list[str]) -> str:
        """具象クラスで実行手順書を構築して返す"""
        pass

    def render_markdown(self, text_parts) -> str:
        """Markdown ドキュメントを構築する"""
        from string import Template
 
        # 決定論的な概要（Overview）の組み立て
        # design.json に summary (仕様概要) があればそれを最優先とし、なければLLM抽出の purpose を使う
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
        
        # 決定論的な説明文の構築
        out_mode = self.design_data.output_mode
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

    def _call_gemini_api(self, request: GeminiRequest, schema):
        """Gemini API を使って構造化 JSON を取得しパースする共通メソッド"""
        response = request.execute(
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2
            )
        )
        try:
            data = json.loads(response.text)
            return schema.model_validate(data)
        except Exception as e:
            print(f"Error parsing Gemini response: {e}", file=sys.stderr)
            print(response.text, file=sys.stderr)
            raise e

    def generate(self, output_dir: str):
        """【共通フロー】仕様書の生成を実行する（テンプレートメソッド）"""
        # 共通プロンプトテンプレートをロード
        from edd_agent_tools.registry import SkillRegistry
        registry = SkillRegistry()
        writer_dir = registry.get_skill_directory("skill-spec-writer")
        prompt_tmpl = writer_dir.load_asset("prompt_common.txt")
            
        prompt = self.build_prompt(prompt_tmpl)
        if self.prompt:
            prompt = f"{prompt}\n\n=== ユーザーからの仕様書生成に関する追加のこだわり指示（最優先） ===\n{self.prompt}"
            
        schema = self.get_pydantic_schema()
        
        # GeminiRequestを用いてマルチパーツ添付を構築
        gemini_request = self.client.request(prompt)
        if self.source_code_dir:
            ref_root = output_dir if output_dir else os.path.dirname(self.source_code_dir)
            gemini_request.add_dir(self.source_code_dir, ref_root=ref_root, file_filter=lambda p: p.endswith(".py"))
        
        # LLMから非決定論的情報の抽出
        text_parts = self._call_gemini_api(gemini_request, schema)
        
        # 決定論的な Markdown 合成
        markdown_content = self.render_markdown(text_parts)
        
        # 保存
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, "SKILL.md")
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        return output_file_path
