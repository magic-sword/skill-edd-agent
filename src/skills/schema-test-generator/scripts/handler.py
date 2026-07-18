from .executor import SkillExecutor

def generate_tests(skill_name: str, output_path: str) -> bool:
    """指定されたスキルのdesign.jsonに基づき、正常系および異常系の単体テストケースを自動生成し、EvalCaseSetフォーマットのJSONとしてファイルに書き出します。

    Args:
        skill_name: テストケースを生成する対象スキルの名前.
        output_path: 生成されたテストケースを書き出すファイルのパス.

    Returns:
        成功した場合は True、失敗した場合は False.
    """
    executor = SkillExecutor()
    res = executor.generate_test_cases(skill_name=skill_name, output_path=output_path)
    return res.success


