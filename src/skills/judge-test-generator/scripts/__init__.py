from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "generate_tests":
        from .handler import generate_tests
        return generate_tests

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['generate_tests']
