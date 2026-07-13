from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "run_test_evaluation":
        from .handler import run_test_evaluation
        return run_test_evaluation

    if name == "Output":
        from .models import Output
        return Output

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["run_test_evaluation", "Output"]
