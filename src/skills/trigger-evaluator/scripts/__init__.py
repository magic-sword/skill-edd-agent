from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "evaluate_trigger":
        from .handler import evaluate_trigger
        return evaluate_trigger

    if name == "EvaluateTriggerOutput":
        from .models import EvaluateTriggerOutput
        return EvaluateTriggerOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['evaluate_trigger', 'EvaluateTriggerOutput']
