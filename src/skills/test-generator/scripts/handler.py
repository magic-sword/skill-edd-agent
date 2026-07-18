from typing import Literal
from .models import GenerateTestCasesOutput
from .executor import SkillExecutor

def generate_test_cases(skill: str, test_type: str) -> GenerateTestCasesOutput:
    """指定されたスキルとテストタイプに基づき、対応するテスト生成スキルを動的にロードし、テストケースを生成してファイルに書き出します。

    Args:
        skill: テストケースを生成する対象のスキル名。
        test_type: 生成するテストケースの種別（例: 'trigger', 'unit', 'integration'）。

    Returns:
        実行結果オブジェクト (GenerateTestCasesOutput)。
    """
    executor = SkillExecutor()
    return executor.generate_test_cases(skill=skill, test_type=test_type)


