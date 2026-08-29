from typing import Any

def __getattr__(name: str) -> Any:
    """evaluation パッケージ内のクラスをアクセス時に初めて動的ロードする遅延インポートハンドラ。"""
    if name in ("SimulationEval", "SimulationEvalRunner"):
        from .evaluation import SimulationEval
        return SimulationEval
        
    if name == "LocalWorkspaceEnv":
        from .environment import LocalWorkspaceEnv
        return LocalWorkspaceEnv

    if name == "RealWorkspaceEnv":
        from .real_env import RealWorkspaceEnv
        return RealWorkspaceEnv

    if name in ("ArtifactApplier", "LocalFileApplier"):
        from .applier import ArtifactApplier, LocalFileApplier
        if name == "ArtifactApplier": return ArtifactApplier
        if name == "LocalFileApplier": return LocalFileApplier

    if name == "GitSandbox":
        from .sandbox import GitSandbox
        return GitSandbox

    if name in ("WorkspaceEnvProtocol", "TestGenerator", "TestExecutor", "EvalRunResult"):
        from .models import WorkspaceEnvProtocol, TestGenerator, TestExecutor, EvalRunResult
        if name == "WorkspaceEnvProtocol": return WorkspaceEnvProtocol
        if name == "TestGenerator": return TestGenerator
        if name == "TestExecutor": return TestExecutor
        if name == "EvalRunResult": return EvalRunResult
        
    if name == "ContractTestRunner":
        from .test_runner import ContractTestRunner
        return ContractTestRunner

    if name in ("EvalCase", "EvalCaseSet", "TrajectoryEvalSet"):
        from .models import EvalCase, EvalCaseSet, TrajectoryEvalSet
        if name == "EvalCase": return EvalCase
        if name == "EvalCaseSet": return EvalCaseSet
        if name == "TrajectoryEvalSet": return TrajectoryEvalSet
        
    if name == "CascadeTestRunner":
        from .cascade_runner import CascadeTestRunner
        return CascadeTestRunner
        
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    "SimulationEval", "SimulationEvalRunner", "LocalWorkspaceEnv", "RealWorkspaceEnv", "ArtifactApplier", 
    "LocalFileApplier", "GitSandbox", "WorkspaceEnvProtocol", "ContractTestRunner",
    "EvalCase", "EvalCaseSet", "TestGenerator", "TestExecutor", "EvalRunResult", "TrajectoryEvalSet",
    "CascadeTestRunner"
]

