from typing import Any

def __getattr__(name: str) -> Any:
    """遅延インポートを実現するための属性解決ハンドラ。"""
    if name == "generate_test_cases":
        from .handler import generate_test_cases
        return generate_test_cases

    if name == "GenerateTestCasesOutput":
        from .models import GenerateTestCasesOutput
        return GenerateTestCasesOutput

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['generate_test_cases', 'GenerateTestCasesOutput']
