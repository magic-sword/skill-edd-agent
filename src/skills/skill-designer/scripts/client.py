from google.genai import types
from edd_agent_tools import SkillDesign, ModuleDesign, clean_pydantic_schema
from edd_agent_tools.gemini import client

class GeminiDesignClient:
    """
    Gemini API を利用してスキル設計を生成するクライアントを提供します。
    """
    def __init__(self):
        self._client = client

    def generate_design(self, contents: list[types.ContentType], response_schema) -> str:
        """
        Gemini API を呼び出し、指定されたスキーマに従って JSON 文字列を生成します。
        """
        response = self._client.generate_content(
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=clean_pydantic_schema(response_schema),
                temperature=0.1
            )
        )
        return response.text
