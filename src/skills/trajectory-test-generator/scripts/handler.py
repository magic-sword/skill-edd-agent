from .executor import TrajectoryTestGenerator

def generate_tests(skill_name: str, output_path: str) -> bool:
    """指定されたスキルの仕様から軌跡テストケース（TrajectoryEvalSet）を生成し、指定パスに保存します。

    Args:
        skill_name: テストケース生成対象の論理スキル名。
        output_path: 生成結果を保存する *.evalset.json の物理パス。

    Returns:
        成功した場合は True、失敗した場合は False。
    """
    generator = TrajectoryTestGenerator()
    return generator.generate_tests(skill_name=skill_name, output_path=output_path)
