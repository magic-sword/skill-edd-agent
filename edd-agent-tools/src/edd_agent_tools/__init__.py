"""
EDD Agent Tools (edd-agent-tools)
=================================

Evaluation-Driven Development (EDD) tools and helper libraries for AI Agent development.
Anthropic Markdown-First & Google ADK 2.0 準拠の自己改善エージェント開発基盤パッケージ。
"""

from typing import Any

# Models
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
from .models.eval import (
    EvalCase,
    EvalCaseSet,
    FailedCaseDetail,
    EvalRunResult,
    EvalDetailReport
)

# Core Entities & Discovery
from .core.entity import Skill, SkillTests
from .state import SkillsState

# Validation & Packaging & Scaffolding
from .validation.validator import SkillValidator, ValidationResult, ValidationIssue
from .packaging.packager import SkillPackager
from .packaging.scaffold import SkillScaffolder

# Evaluation & Sandboxing
from .evaluation.test_runner import ContractTestRunner
from .evaluation.simulation_runner import SimulationEvalRunner
from .evaluation.cascade_runner import CascadeTestRunner
from .evaluation.diagnoser import SkillDiagnoser
from .evaluation.optimizer import SkillOptimizer
from .evaluation.environment import LocalWorkspaceEnv
from .core.protocols import WorkspaceEnvProtocol

# ADK Integration
from .adk.toolset import EddSkillToolset, create_adk_skill_toolset

__version__ = "0.5.0"

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
    "SkillTests",
    "SkillsState",
    # Validation & Packaging
    "SkillValidator",
    "ValidationResult",
    "ValidationIssue",
    "SkillPackager",
    "SkillScaffolder",
    # Evaluation
    "ContractTestRunner",
    "SimulationEvalRunner",
    "CascadeTestRunner",
    "SkillDiagnoser",
    "SkillOptimizer",
    "LocalWorkspaceEnv",
    "WorkspaceEnvProtocol",
    # ADK
    "EddSkillToolset",
    "create_adk_skill_toolset",
]
