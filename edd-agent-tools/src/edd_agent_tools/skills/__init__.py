from typing import Any

def __getattr__(name: str) -> Any:
    """パッケージ内のモジュールをアクセス時に動的ロードする遅延インポートハンドラ。"""
    if name == "SkillsState":
        from edd_agent_tools.state import SkillsState
        return SkillsState
        
    if name in (
        "SkillsStateJson", "SkillEntry", "InheritEntry", "SkillTier",
        "ProjectSkillInfo", "SkillPattern", "SkillLogicDraft",
        "SkillSpec", "SkillMetadata"
    ):
        import edd_agent_tools.models as m
        return getattr(m, name)

    if name == "Skill":
        from edd_agent_tools.skill import Skill
        return Skill

    if name == "SkillTemplateEngine":
        from .template_engine import SkillTemplateEngine
        return SkillTemplateEngine

    if name in ("SkillValidator", "ValidationResult"):
        import edd_agent_tools.validation.validator as v
        return getattr(v, name)

    if name == "SkillCreationEngine":
        from .creator import SkillCreationEngine
        return SkillCreationEngine

    if name == "create_skill":
        from .creator import create_skill
        return create_skill
        
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    "SkillsStateJson",
    "SkillEntry",
    "InheritEntry",
    "SkillTier",
    "ProjectSkillInfo",
    "SkillPattern",
    "SkillLogicDraft",
    "SkillSpec",
    "SkillMetadata",
    "SkillsState",
    "Skill",
    "SkillTemplateEngine",
    "SkillValidator",
    "ValidationResult",
    "SkillCreationEngine",
    "create_skill"
]


