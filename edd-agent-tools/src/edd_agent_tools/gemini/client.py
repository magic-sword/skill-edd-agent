import os
from typing import Any
from google.genai import types
from .base import BaseGeminiClient
from .direct_client import DirectGeminiClient
from .agy_client import AgyGeminiClient

from .request import GeminiRequest

class GeminiClient(BaseGeminiClient):
    """環境変数に基づき、Agy または Direct の適切な実装に処理を委譲するプロキシクライアント。
    
    TUI/CLI連携時のクレジット共有 (agy) と、直接APIキーを使用する API 呼び出しの双方を透過的に切り替えます。
    """
    def __init__(self, client_type: str | None = None):
        """GeminiClient を初期化します。
        
        Args:
            client_type: 使用するクライアント種別 ('agy' または 'gemini')。
                指定がない場合は環境変数 GEMINI_CLIENT_TYPE (デフォルト: 'gemini') に従います。
        """
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
        """指定されたコンテンツと構成設定を使用して、Gemini API から応答を生成します。

        Args:
            contents: 生成対象のプロンプトテキスト、ファイル、または GeminiRequest オブジェクト。
            config: API生成の設定オプション（response_schema や temperature 等）。
            model: 使用するモデル名（任意）。指定がない場合はデフォルトモデルが使用されます。
            **kwargs: その他のクライアント固有の引数。

        Returns:
            types.GenerateContentResponse: APIから返却される応答オブジェクト。
        """
        return self._impl.generate_content(contents, config=config, model=model, **kwargs)

# シングルトンオブジェクトの作成
client = GeminiClient()

def request(prompt: str) -> GeminiRequest:
    """共通クライアントにバインドされた新しい GeminiRequest インスタンスを生成します。
    
    Args:
        prompt: メインのプロンプトテキスト。
        
    Returns:
        GeminiRequest: メソッドチェーンでリクエストを構築可能なリクエストオブジェクト。
    """
    return GeminiRequest(prompt, client=client)

def generate_content(contents, config=None, **kwargs):
    """共通クライアントを介してコンテンツ生成を直接実行します。
    
    Args:
        contents: 生成対象のコンテンツ。
        config: 生成の設定オプション。
        **kwargs: 追加のパラメータ。
        
    Returns:
        types.GenerateContentResponse: 応答オブジェクト。
    """
    return client.generate_content(contents, config=config, **kwargs)





