from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "run_tier2_test":
        from .handler import run_tier2_test
        return run_tier2_test

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['run_tier2_test']
