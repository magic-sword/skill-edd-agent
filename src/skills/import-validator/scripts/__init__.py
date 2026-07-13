from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "validate_skill_import":
        from .handler import validate_skill_import
        return validate_skill_import

    if name == "Output":
        from .models import Output
        return Output

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["validate_skill_import", "Output"]
