from typing import Any

def __getattr__(name: str) -> Any:
    """evaluation パッケージ内のクラスをアクセス時に初めて動的ロードする遅延インポートハンドラ。"""
    if name in ("SkillEval", "UnitEval", "TriggerEval"):
        from .evaluation import SkillEval, UnitEval, TriggerEval
        if name == "SkillEval": return SkillEval
        if name == "UnitEval": return UnitEval
        if name == "TriggerEval": return TriggerEval
        
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = ["SkillEval", "UnitEval", "TriggerEval"]
