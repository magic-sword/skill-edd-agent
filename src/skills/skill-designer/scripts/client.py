import time
from google.genai import types
from edd_agent_tools.gemini import get_gemini_client
from edd_agent_tools.models import SkillDesign

class GeminiDesignClient:
    """
    Gemini API を利用してスキル設計を生成するクライアントを提供します。
    """
    def __init__(self):
        self._client = get_gemini_client()

    def generate_design(
        self, 
        contents: list[types.ContentType],
        max_retries: int = 3,
        retry_delay: int = 2
    ) -> str:
        """
        Gemini API を呼び出し、スキル設計の JSON 文字列を生成します。
        一時的なエラーに対してリトライ処理を行います。

        Args:
            contents: Gemini API に送信するマルチパートコンテンツ。
            max_retries: 最大リトライ回数。
            retry_delay: リトライ間の初期遅延時間（秒）。

        Returns:
            Gemini API からの応答テキスト（JSON文字列）。

        Raises:
            Exception: 指定されたリトライ回数を超えてもAPI呼び出しが成功しなかった場合。
        """
        response = None
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=SkillDesign,
                        temperature=0.1
                    )
                )
                return response.text
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Gemini API 呼び出しエラー: {e}")
                print(f"Gemini API 呼び出しエラー (試行 {attempt + 1}/{max_retries}): {e}。{retry_delay}秒後に再試行します...")
                time.sleep(retry_delay)
                retry_delay *= 2
        # ここには到達しないはずだが、念のためNoneを返さない
        raise Exception("Gemini API 呼び出しが予期せず失敗しました。")
