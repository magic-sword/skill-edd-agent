from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "execute_adk_simulation":
        from .handler import execute_adk_simulation
        return execute_adk_simulation

    if name == "ExecuteAdkSimulationOutput":
        from .models import ExecuteAdkSimulationOutput
        return ExecuteAdkSimulationOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['execute_adk_simulation', 'ExecuteAdkSimulationOutput']
