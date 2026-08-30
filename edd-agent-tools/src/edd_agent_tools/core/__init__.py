"""
Core Module for edd-agent-tools

共通ドメインモデル、状態管理、プロトコル定義をエクスポートします。
"""

from .models import (
    SkillTier,
    SkillEntry,
    InheritEntry,
    ProjectSkillInfo,
    SkillsStateJson,
    SkillPattern,
    ModuleType,
    DecisionBranch,
    StepInstruction,
    ResourcePlan,
    SkillLogicDraft,
    SkillFrontmatter,
    SkillSpec,
    SkillMetadata,
)
from .skill import Skill
from .state import SkillsState
from .protocols import WorkspaceEnvProtocol

__all__ = [
    "SkillTier",
    "SkillEntry",
    "InheritEntry",
    "ProjectSkillInfo",
    "SkillsStateJson",
    "SkillPattern",
    "ModuleType",
    "DecisionBranch",
    "StepInstruction",
    "ResourcePlan",
    "SkillLogicDraft",
    "SkillFrontmatter",
    "SkillSpec",
    "SkillMetadata",
    "Skill",
    "SkillsState",
    "WorkspaceEnvProtocol",
]
