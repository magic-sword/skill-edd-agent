from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "skill_developer":
        from .handler import skill_developer
        return skill_developer

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["skill_developer"]
