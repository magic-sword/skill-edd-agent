from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "validate_design":
        from .handler import validate_design
        return validate_design

    if name == "ValidateDesignOutput":
        from .models import ValidateDesignOutput
        return ValidateDesignOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['validate_design', 'ValidateDesignOutput']
