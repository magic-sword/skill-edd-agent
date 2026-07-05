import os
from collections.abc import Callable
from typing import Any

class GeminiRequest:
    """
    Gemini APIへの1回のリクエスト（プロンプトおよび添付ファイルコンテキスト）を組み立てて実行するクラス。
    メソッドチェーンに対応し、流れるような記述でリクエストを構築できます。
    """
    def __init__(self, prompt: str, client=None):
        self.prompt = prompt
        self.parts = [prompt] if prompt else []
        self._client = client

    def add_dir(self, directory: str, ref_root: str | None = None, file_filter: Callable[[str], bool] | None = None) -> "GeminiRequest":
        """
        指定されたディレクトリ配下のファイルをスキャンし、
        file_filter によって許可されたファイルをそれぞれ独立したテキストパーツとして添付に追加します。
        """
        if not os.path.exists(directory):
            return self
            
        if not os.path.isdir(directory):
            if file_filter is None or file_filter(directory):
                self.add_file(directory, ref_root)
            return self

        target_files = []
        for root, dirs, files in os.walk(directory):
            for f in files:
                file_path = os.path.join(root, f)
                if file_filter is None or file_filter(file_path):
                    target_files.append(file_path)

        if not target_files:
            return self

        ref_root = ref_root or os.path.dirname(directory)
        for file_path in sorted(target_files):
            rel_path = os.path.relpath(file_path, ref_root)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.parts.append(f"# --- File: {rel_path} ---\n{content}")
            except Exception as e:
                print(f"Warning: Failed to load file {file_path} for Gemini attachment: {e}")
        return self

    def add_file(self, file_path: str, ref_root: str | None = None) -> "GeminiRequest":
        """単一のファイルを独立したテキストパーツとして添付に追加します。"""
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return self
            
        ref_root = ref_root or os.path.dirname(file_path)
        rel_path = os.path.relpath(file_path, ref_root)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.parts.append(f"# --- File: {rel_path} ---\n{content}")
        except Exception as e:
            print(f"Warning: Failed to load file {file_path} for Gemini attachment: {e}")
        return self

    def add_text(self, text: str) -> "GeminiRequest":
        """任意のテキストコンテンツをパーツとして追加します。"""
        if text:
            self.parts.append(text)
        return self

    def build(self) -> list[str]:
        """Gemini API に渡すための contents リストを返します。"""
        return self.parts

    def execute(self, config: Any = None, model: str | None = None, **kwargs: Any) -> Any:
        """このリクエストで組み立てられたコンテンツを使用して、紐づくクライアントから API を呼び出します。"""
        if not self._client:
            raise RuntimeError("Error: This GeminiRequest is not associated with a GeminiClient.")
        return self._client.generate_content(
            contents=self,
            config=config,
            model=model,
            **kwargs
        )
