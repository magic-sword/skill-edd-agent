from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "skill_designer":
        from .handler import skill_designer
        return skill_designer

    if name == "SkillDesignerOutput":
        from .models import SkillDesignerOutput
        return SkillDesignerOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['skill_designer', 'SkillDesignerOutput']
