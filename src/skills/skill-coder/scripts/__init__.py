from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "code_skill":
        from .handler import code_skill
        return code_skill

    if name == "Output":
        from .models import Output
        return Output

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["code_skill", "Output"]
