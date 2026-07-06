from typing import Any

def __getattr__(name: str) -> Any:
    """パッケージ内のモジュールをアクセス時に初めて動的ロードする遅延インポートハンドラ。"""
    if name == "GeminiClient":
        from .client import GeminiClient
        return GeminiClient
        
    if name == "GeminiRequest":
        from .request import GeminiRequest
        return GeminiRequest
        
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    "GeminiClient",
    "GeminiRequest"
]
