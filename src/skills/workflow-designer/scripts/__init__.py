from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "workflow_designer":
        from .handler import workflow_designer
        return workflow_designer

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['workflow_designer']
