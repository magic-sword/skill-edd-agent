from typing import Any
from google.genai import types

class BaseGeminiClient:
    """Gemini API クライアントの抽象基本クラス。"""
    def request(self, prompt: str = ""):
        """流れるようなリクエストを構築するためのビルダー（GeminiRequest）を生成して返します"""
        from .request import GeminiRequest
        return GeminiRequest(prompt, client=self)

    def generate_content(
        self,
        contents: Any,
        config: types.GenerateContentConfig | None = None,
        model: str | None = None,
        **kwargs: Any
    ) -> types.GenerateContentResponse:
        """コンテンツ生成を行います。サブクラスで実装してください。"""
        raise NotImplementedError("Subclasses must implement generate_content")
