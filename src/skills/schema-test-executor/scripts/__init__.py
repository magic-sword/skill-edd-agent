from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "run_tests":
        from .handler import run_tests
        return run_tests

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['run_tests']

