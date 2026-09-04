"""
Unified Domain Models for edd-agent-tools

Anthropic Agent Skills & Google ADK 2.0 準拠のコアデータモデル定義。
"""

from .spec import (
    SkillPattern,
    ModuleType,
    SkillFrontmatter,
    SkillSpec,
    SkillMetadata
)
from .state import (
    SkillTier,
    SkillEntry,
    InheritEntry,
    ProjectSkillInfo,
    SkillsStateJson
)

# 評価系モデルの遅延ロードマップ (PEP 562)
_EVAL_MODELS = {
    "EvalCase",
    "EvalCaseSet",
    "FailedCaseDetail",
    "EvalRunResult",
    "EvalDetailReport"
}


def __getattr__(name: str):
    if name in _EVAL_MODELS:
        from . import eval as _eval_module
        return getattr(_eval_module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "SkillPattern",
    "ModuleType",
    "SkillFrontmatter",
    "SkillSpec",
    "SkillMetadata",
    "SkillTier",
    "SkillEntry",
    "InheritEntry",
    "ProjectSkillInfo",
    "SkillsStateJson",
    "EvalCase",
    "EvalCaseSet",
    "FailedCaseDetail",
    "EvalRunResult",
    "EvalDetailReport"
]
