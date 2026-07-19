from .models import AddNumbersOutput
from .executor import SkillExecutor

def add_numbers(a: int, b: int) -> AddNumbersOutput:
    """2つの整数を足し算して結果を返します。

    Args:
        a: 足し算の最初の整数。
        b: 足し算の2番目の整数。

    Returns:
        実行結果オブジェクト (AddNumbersOutput)。
    """
    executor = SkillExecutor()
    return executor.add_numbers(a=a, b=b)

