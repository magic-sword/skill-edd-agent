from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートハンドラ。"""
    if name == "run_first_test":
        from .handler import run_first_test
        return run_first_test

    if name == "RunFirstTestOutput":
        from .models import RunFirstTestOutput
        return RunFirstTestOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['run_first_test', 'RunFirstTestOutput']
