from typing import Any
from edd_agent_tools.gemini import client

class GeminiClient:
    """Gemini API と対話するためのクライアント。"""

    def __init__(self):
        pass

    def call_gemini_api(self, prompt: str, response_schema: Any = None) -> Any:
        """
        Gemini API を呼び出し、設計と実装の整合性を検証します。
        ファイルの内容はプロンプト内に直接埋め込む形式で渡されます。

        Args:
            prompt: Gemini に送信するプロンプト。
            response_schema: 期待される構造化出力のPydanticモデル。

        Returns:
            Any: Gemini API からの応答オブジェクト。
        """
        config = None
        if response_schema:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema
            )
        return client.request(prompt).execute(config=config)
