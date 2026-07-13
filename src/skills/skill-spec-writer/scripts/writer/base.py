import os
import sys
import json
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from typing import Union
from edd_agent_tools.models import SkillDesign, WorkflowDesign
from edd_agent_tools.gemini import GeminiRequest

class BaseSpecWriter(ABC):
    def __init__(self, design_data: Union[SkillDesign, WorkflowDesign], source_code_dir: str, prompt: str | None = None):
        self.design_data = design_data
        self.name = design_data.name
        self.source_code_dir = source_code_dir
        self.prompt = prompt
        
        from edd_agent_tools.gemini import client
        self.client = client

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

    @abstractmethod
    def render_markdown(self, text_parts) -> str:
        """Markdown ドキュメントを構築する"""
        pass

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
        from edd_agent_tools.skills import SkillsState
        state = SkillsState()
        writer_skill = state.get_skill("skill-spec-writer")
        prompt_tmpl = writer_skill.load_asset("prompt_common.txt")
            
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
