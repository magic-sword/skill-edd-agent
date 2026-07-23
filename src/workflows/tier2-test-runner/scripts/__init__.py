from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "tier2_test_runner":
        from .handler import tier2_test_runner
        return tier2_test_runner

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["tier2_test_runner"]
