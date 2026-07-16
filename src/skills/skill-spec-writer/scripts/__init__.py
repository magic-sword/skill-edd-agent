from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "generate_skill_spec":
        from .handler import generate_skill_spec
        return generate_skill_spec

    if name == "GenerateSkillSpecOutput":
        from .models import GenerateSkillSpecOutput
        return GenerateSkillSpecOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['generate_skill_spec', 'GenerateSkillSpecOutput']
