from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "skill_coder":
        from .handler import skill_coder
        return skill_coder

    if name == "SkillCoderOutput":
        from .models import SkillCoderOutput
        return SkillCoderOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['skill_coder', 'SkillCoderOutput']
