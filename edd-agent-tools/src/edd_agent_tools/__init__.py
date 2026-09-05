"""
EDD Agent Tools (edd-agent-tools)
=================================

Evaluation-Driven Development (EDD) tools and helper libraries for AI Agent development.
Anthropic Markdown-First & Google ADK 2.0 準拠の自己改善エージェント開発基盤パッケージ。
"""

import sys
import importlib
from typing import Any

# Models (軽量・必須)
from .models.spec import (
    SkillPattern,
    ModuleType,
    SkillFrontmatter,
    SkillSpec,
    SkillMetadata
)
from .models.state import (
    SkillTier,
    SkillEntry,
    InheritEntry,
    ProjectSkillInfo,
    SkillsStateJson
)

# Core Entities & Discovery
from .core.entity import Skill, SkillPackage, SkillTests
from .state import SkillsState

# Validation & Packaging & Scaffolding
from .validation.validator import SkillValidator, ValidationResult, ValidationIssue
from .packaging.packager import SkillPackager
from .packaging.scaffold import SkillScaffolder

# ADK 2.0 Integration (Core Toolset & Registry)
from .adk.toolset import SkillToolset, EddSkillToolset, EddSkillRegistry, create_adk_skill_toolset

__version__ = "0.7.0"

# 評価・メタモジュールの遅延ロード定義（起動速度最適化および循環・不要依存の連鎖回避）
_LAZY_IMPORTS = {
    "EvalCase": ".models.eval",
    "EvalCaseSet": ".models.eval",
    "FailedCaseDetail": ".models.eval",
    "EvalRunResult": ".models.eval",
    "EvalDetailReport": ".models.eval",
    "ContractTestRunner": ".evaluation.test_runner",
    "SimulationEvalRunner": ".evaluation.simulation_runner",
    "CascadeTestRunner": ".evaluation.cascade_runner",
    "SkillDiagnoser": ".evaluation.diagnoser",
    "SkillOptimizer": ".evaluation.optimizer",
    "LocalWorkspaceEnv": ".evaluation.environment",
    "AdkEvalAdapter": ".evaluation.adk_eval",
    "CoLoadedEvalRunner": ".evaluation.co_loaded_runner",
    "WorkspaceEnvProtocol": ".core.protocols",
    "DescriptionOptimizer": ".meta.description_optimizer",
    "TraceHarvester": ".meta.trace_harvester",
    "CapabilityProfile": ".meta.capability_profile",
    "CapabilityProfileManager": ".meta.capability_profile",
}


def __getattr__(name: str) -> Any:
    """遅延インポートハンドラー"""
    if name in _LAZY_IMPORTS:
        module_path = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path, package=__name__)
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    """dir() 呼び出し時に遅延ロード対象も含めて一覧表示"""
    return sorted(list(globals().keys()) + list(_LAZY_IMPORTS.keys()))


__all__ = [
    # Models
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
    "EvalDetailReport",
    # Core
    "Skill",
    "SkillPackage",
    "SkillTests",
    "SkillsState",
    # Validation & Packaging
    "SkillValidator",
    "ValidationResult",
    "ValidationIssue",
    "SkillPackager",
    "SkillScaffolder",
    # ADK
    "SkillToolset",
    "EddSkillToolset",
    "EddSkillRegistry",
    "create_adk_skill_toolset",
    # Evaluation (Lazy)
    "ContractTestRunner",
    "SimulationEvalRunner",
    "CascadeTestRunner",
    "SkillDiagnoser",
    "SkillOptimizer",
    "LocalWorkspaceEnv",
    "AdkEvalAdapter",
    "CoLoadedEvalRunner",
    "WorkspaceEnvProtocol",
    # Meta-Skills (Lazy)
    "DescriptionOptimizer",
    "TraceHarvester",
    "CapabilityProfile",
    "CapabilityProfileManager",
]
