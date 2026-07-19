from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "add_numbers":
        from .handler import add_numbers
        return add_numbers

    if name == "AddNumbersOutput":
        from .models import AddNumbersOutput
        return AddNumbersOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['add_numbers', 'AddNumbersOutput']
