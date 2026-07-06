from google.genai import types
from edd_agent_tools import GeminiClient, SkillDesign, ModuleDesign

class GeminiDesignClient:
    """
    Gemini API を利用してスキル設計を生成するクライアントを提供します。
    """
    def __init__(self):
        self._client = GeminiClient()

    def generate_design(self, contents: list[types.ContentType]) -> str:
        """
        Gemini API を呼び出し、スキル設計の JSON 文字列を生成します。
        """
        response = self._client.generate_content(
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ModuleDesign,
                temperature=0.1
            )
        )
        return response.text
