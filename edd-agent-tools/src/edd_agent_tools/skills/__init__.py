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
        
    if name == "Skill":
        from .skill import Skill
        return Skill
        
    raise AttributeError(f"module {__name__} has no attribute {name}")

# エディタの自動補完や静的解析ツールが公開シンボルを正しく認識できるように __all__ を定義
__all__ = [
    "SkillsStateJson",
    "SkillEntry",
    "InheritEntry",
    "SkillTier",
    "ProjectSkillInfo",
    "SkillsState",
    "Skill"
]
