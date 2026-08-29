from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "tier1_skill_onboarding":
        from .handler import tier1_skill_onboarding
        return tier1_skill_onboarding

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["tier1_skill_onboarding"]
