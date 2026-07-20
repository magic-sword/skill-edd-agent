"""ユーティリティ関数を提供するモジュール。"""

def to_lowercase(text: str) -> str:
    """入力された文字列の英字をすべて小文字に変換します。

    Args:
        text: 変換対象の文字列。

    Returns:
        すべて小文字に変換された文字列。
    """
    return text.lower()
