from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "skill_coder":
        from .handler import skill_coder
        return skill_coder

    if name == "SkillCoderOutput":
        from .models import SkillCoderOutput
        return SkillCoderOutput

    if name == "Output":
        from .models import Output
        return Output

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['skill_coder', 'SkillCoderOutput', 'Output']
