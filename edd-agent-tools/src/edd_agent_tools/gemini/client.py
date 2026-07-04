import os
from google import genai

def get_gemini_client() -> genai.Client:
    """
    環境変数 GEMINI_API_KEY を使用して genai.Client インスタンスを取得します。
    環境変数が設定されていない場合は ValueError をスローします。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Error: GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)
