from .executor import SkillExecutor

def generate_tests(skill_name: str, output_path: str) -> bool:
    """指定されたスキルのSKILL.md仕様書を基に、仕様の静的チェックを行い、合格した場合はインテント評価用のテストケースを自動生成してファイルに書き出すワークフローを実行します。

    Args:
        skill_name: テストケースを生成する対象スキルの名前。
        output_path: 生成されたテストケースを保存するファイルのパス（TrajectoryEvalSetフォーマットのJSON）。

    Returns:
        成功した場合は True、失敗した場合は False。
    """
    executor = SkillExecutor()
    return executor.generate_trigger_tests(skill_name=skill_name, output_path=output_path)
