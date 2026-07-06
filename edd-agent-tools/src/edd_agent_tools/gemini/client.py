import os
import time
from typing import Any
from google import genai
from google.genai import types

class GeminiClient:
    """共通の堅牢な Gemini API クライアント。

    モデル名、リトライ回数、タイムアウトなどの中央集約的な管理と、エラー時の自動リトライを提供します。

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
    def __init__(self):
        self.default_model = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
        self.initial_delay = float(os.getenv("GEMINI_RETRY_DELAY", "2.0"))
        self._client = self._get_genai_client()

    def _get_genai_client(self) -> genai.Client:
        """環境変数 GEMINI_API_KEY を使用して genai.Client を初期化します"""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Error: GEMINI_API_KEY environment variable is not set.")
        return genai.Client(api_key=api_key)

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
        """
        堅牢な指数バックオフリトライとタイムアウト制御を備えた中央集約的なコンテンツ生成。
        """
        # response_schema が Pydantic の BaseModel サブクラスである場合、
        # Gemini API が受け入れられないカスタム属性を除外したクリーンなモデルに差し替える
        if config and getattr(config, "response_schema", None) is not None:
            from pydantic import BaseModel
            from edd_agent_tools.models import clean_pydantic_schema

            orig_schema = config.response_schema
            if isinstance(orig_schema, type) and issubclass(orig_schema, BaseModel):
                config.response_schema = clean_pydantic_schema(orig_schema)

        from .request import GeminiRequest
        if isinstance(contents, GeminiRequest):
            actual_contents = contents.build()
        else:
            actual_contents = contents

        target_model = model or self.default_model
        delay = self.initial_delay
        
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=actual_contents,
                    config=config,
                    **kwargs
                )
                return response
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    break
                
                print(f"⚠️ Gemini API Error (Attempt {attempt+1}/{self.max_retries+1}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
                
        raise Exception(f"Gemini API 呼び出しが {self.max_retries+1} 回の試行後に失敗しました。最後のエラー: {last_exception}")
