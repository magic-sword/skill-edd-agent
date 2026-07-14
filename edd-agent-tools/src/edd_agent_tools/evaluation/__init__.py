from typing import Any

def __getattr__(name: str) -> Any:
    """evaluation パッケージ内のクラスをアクセス時に初めて動的ロードする遅延インポートハンドラ。"""
    if name == "SimulationEval":
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

    if name == "WorkspaceEnvProtocol":
        from .models import WorkspaceEnvProtocol
        return WorkspaceEnvProtocol
        
    if name == "SchemaDrivenTestRunner":
        from .test_runner import SchemaDrivenTestRunner
        return SchemaDrivenTestRunner
        
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    "SimulationEval", "LocalWorkspaceEnv", "RealWorkspaceEnv", "ArtifactApplier", 
    "LocalFileApplier", "GitSandbox", "WorkspaceEnvProtocol", "SchemaDrivenTestRunner"
]
