import os
import sys
import json
from abc import ABC, abstractmethod
from google.adk.tools import ToolContext

from google import genai
from google.genai import types


from edd_agent_tools.models import SkillDesign

class BaseSpecWriter(ABC):
    def __init__(self, design_data: SkillDesign, source_code_dir: str, tool_context: ToolContext):
        self.design_data = design_data
        self.name = design_data.name
        self.source_code_dir = source_code_dir
        self.tool_context = tool_context
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Error: GEMINI_API_KEY environment variable is not set.")
        self.client = genai.Client(api_key=api_key)

    @abstractmethod
    def get_pydantic_schema(self):
        """抽出用の Pydantic モデルを返す"""
        pass

    @abstractmethod
    def build_prompt(self, prompt_tmpl: str) -> str:
        """LLM に渡すプロンプトを構築する"""
        pass

    @abstractmethod
    def render_markdown(self, text_parts) -> str:
        """Markdown ドキュメントを構築する"""
        pass

    def _call_gemini_api(self, contents: list[str], schema):
        """Gemini API を使って構造化 JSON を取得しパースする共通メソッド"""
        from edd_agent_tools.utils.schema import remove_additional_properties
        schema_dict = schema.model_json_schema()
        clean_schema = remove_additional_properties(schema_dict)
        
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=clean_schema,
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
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(script_dir, "..", "assets", "prompt_common.txt")
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
            
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_tmpl = f.read()
            
        prompt = self.build_prompt(prompt_tmpl)
        schema = self.get_pydantic_schema()
        
        # GeminiContentBuilderを用いてマルチパーツ添付を構築
        from edd_agent_tools.gemini import GeminiContentBuilder
        builder = GeminiContentBuilder(prompt)
        if self.source_code_dir:
            ref_root = output_dir if output_dir else os.path.dirname(self.source_code_dir)
            builder.add_dir(self.source_code_dir, ref_root=ref_root, file_filter=lambda p: p.endswith(".py"))
        contents = builder.build()
        
        # LLMから非決定論的情報の抽出
        text_parts = self._call_gemini_api(contents, schema)
        
        # 決定論的な Markdown 合成
        markdown_content = self.render_markdown(text_parts)
        
        # 保存
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, "SKILL.md")
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        return output_file_path
