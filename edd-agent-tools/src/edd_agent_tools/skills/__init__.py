from typing import Any

def __getattr__(name: str) -> Any:
    """パッケージ内のモジュールをアクセス時に初めて動的ロードする遅延インポートハンドラ。"""
    if name == "SkillsState":
        from .state import SkillsState
        return SkillsState
        
    if name == "SkillsStateJson":
        from .models import SkillsStateJson
        return SkillsStateJson
        
    if name == "SkillEntry":
        from .models import SkillEntry
        return SkillEntry
        
    if name == "InheritEntry":
        from .models import InheritEntry
        return InheritEntry
        
    if name == "SkillTier":
        from .models import SkillTier
        return SkillTier
        
    if name == "ProjectSkillInfo":
        from .models import ProjectSkillInfo
        return ProjectSkillInfo
        
    if name == "SkillPattern":
        from .models import SkillPattern
        return SkillPattern

    if name == "SkillLogicDraft":
        from .models import SkillLogicDraft
        return SkillLogicDraft

    if name == "SkillSpec":
        from .models import SkillSpec
        return SkillSpec

    if name == "SkillMetadata":
        from .models import SkillMetadata
        return SkillMetadata

    if name == "Skill":
        from .skill import Skill
        return Skill

    if name == "SkillTemplateEngine":
        from .template_engine import SkillTemplateEngine
        return SkillTemplateEngine

    if name == "SkillValidator":
        from .validator import SkillValidator
        return SkillValidator

    if name == "ValidationResult":
        from .validator import ValidationResult
        return ValidationResult

    if name == "SkillTests":
        from .tests import SkillTests
        return SkillTests

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
    "SkillTests",
    "SkillCreationEngine",
    "create_skill"
]

