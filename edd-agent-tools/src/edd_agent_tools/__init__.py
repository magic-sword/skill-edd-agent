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
from .models.draft import (
    DecisionBranch,
    StepInstruction,
    ResourcePlan,
    SkillLogicDraft
)
from .models.state import (
    SkillTier,
    SkillEntry,
    InheritEntry,
    ProjectSkillInfo,
    SkillsStateJson
)
from .models.eval import (
    ExpectedResultType,
    EvalCase,
    EvalCaseSet,
    FailedCaseDetail,
    EvalRunResult,
    EvalDetailReport
)

# Core Entities & Discovery
from .skill import Skill
from .state import SkillsState

# Validation & Creation
from .validation.validator import SkillValidator, ValidationResult, ValidationIssue
from .skills.template_engine import SkillTemplateEngine
from .skills.creator import SkillCreationEngine

# Evaluation & Sandboxing
from .evaluation.test_runner import ContractTestRunner
from .evaluation.simulation_runner import SimulationEvalRunner
from .evaluation.cascade_runner import CascadeTestRunner
from .evaluation.diagnoser import SkillDiagnoser
from .evaluation.optimizer import SkillOptimizer
from .evaluation.environment import LocalWorkspaceEnv
from .evaluation.models import WorkspaceEnvProtocol

# ADK Integration
from .adk.toolset import EddSkillToolset

__version__ = "0.3.0"

__all__ = [
    # Models
    "SkillPattern",
    "ModuleType",
    "SkillFrontmatter",
    "SkillSpec",
    "SkillMetadata",
    "DecisionBranch",
    "StepInstruction",
    "ResourcePlan",
    "SkillLogicDraft",
    "SkillTier",
    "SkillEntry",
    "InheritEntry",
    "ProjectSkillInfo",
    "SkillsStateJson",
    "ExpectedResultType",
    "EvalCase",
    "EvalCaseSet",
    "FailedCaseDetail",
    "EvalRunResult",
    "EvalDetailReport",
    # Core
    "Skill",
    "SkillsState",
    # Validation & Creation
    "SkillValidator",
    "ValidationResult",
    "ValidationIssue",
    "SkillTemplateEngine",
    "SkillCreationEngine",
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
]
