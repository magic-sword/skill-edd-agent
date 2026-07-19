
from .models import AddNumbersOutput

class SkillExecutor:
    """2つの整数を足し算して結果を返します。"""
    def __init__(self):
        # 必要な初期化処理をここに記述します
        pass

    def add_numbers(self, a: int, b: int) -> AddNumbersOutput:
        """2つの整数を足し算して結果を返します。

        Args:
            a: 足し算の最初の整数。
            b: 足し算の2番目の整数。

        Returns:
            実行結果オブジェクト (AddNumbersOutput)。
        """
        result = a + b
        return AddNumbersOutput(value=str(result))
