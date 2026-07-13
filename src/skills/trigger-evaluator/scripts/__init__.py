from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "evaluate_trigger":
        from .handler import evaluate_trigger
        return evaluate_trigger

    if name == "Output":
        from .models import Output
        return Output

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["evaluate_trigger", "Output"]
