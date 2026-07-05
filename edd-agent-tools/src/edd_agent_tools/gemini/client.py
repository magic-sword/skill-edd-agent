import os
import time
from typing import Any
from google import genai
from google.genai import types

def get_gemini_client() -> genai.Client:
    """
    環境変数 GEMINI_API_KEY を使用して genai.Client インスタンスを取得します。
    環境変数が設定されていない場合は ValueError をスローします。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Error: GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)

class GeminiClient:
    """
    edd-agent-tools 共通の堅牢な Gemini API クライアント。
    モデル名、リトライ回数、タイムアウトなどの中央集約的な管理と、エラー時の自動リトライを提供します。
    """
    def __init__(self):
        self.default_model = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")
        self.max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
        self.initial_delay = float(os.getenv("GEMINI_RETRY_DELAY", "2.0"))
        self._client = get_gemini_client()

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
        target_model = model or self.default_model
        delay = self.initial_delay
        
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=contents,
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
