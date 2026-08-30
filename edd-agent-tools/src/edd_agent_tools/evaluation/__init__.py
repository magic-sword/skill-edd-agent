"""
Evaluation Subpackage for edd-agent-tools

決定論的多層評価、契約テスト、サンドボックス環境、連鎖テスト、および自己診断エンジン。
"""

from typing import Any

from edd_agent_tools.core.protocols import WorkspaceEnvProtocol
from edd_agent_tools.models import (
    ExpectedResultType,
    EvalCase,
    EvalCaseSet,
    FailedCaseDetail,
    EvalRunResult,
    EvalDetailReport
)
from .environment import LocalWorkspaceEnv
from .real_env import RealWorkspaceEnv
from .test_runner import ContractTestRunner
from .simulation_runner import SimulationEvalRunner
from .cascade_runner import CascadeTestRunner
from .diagnoser import SkillDiagnoser
from .optimizer import SkillOptimizer
from .generator import EvalSetGenerator, generate_evalset

__all__ = [
    "WorkspaceEnvProtocol",
    "ExpectedResultType",
    "EvalCase",
    "EvalCaseSet",
    "FailedCaseDetail",
    "EvalRunResult",
    "EvalDetailReport",
    "LocalWorkspaceEnv",
    "RealWorkspaceEnv",
    "ContractTestRunner",
    "SimulationEvalRunner",
    "CascadeTestRunner",
    "SkillDiagnoser",
    "SkillOptimizer",
    "EvalSetGenerator",
    "generate_evalset"
]
