import os
from typing import Any
from google.genai import types
from .base import BaseGeminiClient
from .direct_client import DirectGeminiClient
from .agy_client import AgyGeminiClient

from .request import GeminiRequest

class GeminiClient(BaseGeminiClient):
    """環境変数に基づき、Agy または Direct の適切な実装に処理を委譲するプロキシクライアント。"""
    def __init__(self, client_type: str | None = None):
        c_type = client_type or os.getenv("GEMINI_CLIENT_TYPE", "gemini")
        if c_type == "agy":
            self._impl = AgyGeminiClient()
        else:
            self._impl = DirectGeminiClient()

    def generate_content(
        self,
        contents: Any,
        config: types.GenerateContentConfig | None = None,
        model: str | None = None,
        **kwargs: Any
    ) -> types.GenerateContentResponse:
        """内部の具象クライアント実装に呼び出しを委譲します。"""
        return self._impl.generate_content(contents, config=config, model=model, **kwargs)

# シングルトンオブジェクトの作成
client = GeminiClient()

def request(prompt: str) -> GeminiRequest:
    """共通クライアントを介して GeminiRequest インスタンスを生成します。"""
    return GeminiRequest(prompt, client=client)

def generate_content(contents, config=None, **kwargs):
    """共通クライアントを介してコンテンツ生成を実行します。"""
    return client.generate_content(contents, config=config, **kwargs)





