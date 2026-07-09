import os
from typing import Any
from google.genai import types
from .base import BaseGeminiClient
from .direct_client import DirectGeminiClient
from .agy_client import AgyGeminiClient

class GeminiClient(BaseGeminiClient):
    """共通の堅牢な Gemini API クライアントインターフェース。

    環境変数 GEMINI_CLIENT_TYPE="agy" が指定されている場合は、Antigravity CLI (agy) を
    LLM バックエンドとして使用する AgyGeminiClient のインスタンスを動的に生成して返します。

    Examples:
        >>> from edd_agent_tools.gemini import GeminiClient
        >>> client = GeminiClient()
        >>> response = (client.request("指示プロンプト...")
        ...                   .add_dir(
        ...                       directory="/workspace/src/skills/my-skill/scripts",
        ...                       ref_root="/workspace/src/skills/my-skill",
        ...                       file_filter=lambda path: path.endswith(".py")
        ...                   )
        ...                   .execute())
    """
    def __new__(cls, *args, **kwargs):
        # GeminiClient 自体のインスタンス化時に、環境変数で動的に具象クラスを選択して返します。
        if cls is GeminiClient:
            client_type = os.getenv("GEMINI_CLIENT_TYPE", "gemini")
            if client_type == "agy":
                return super().__new__(AgyGeminiClient)
            else:
                return super().__new__(DirectGeminiClient)
        return super().__new__(cls)





