from .executor import SkillExecutor

def run_test_evaluation(
    skill: str,
    eval_set_path: str,
    threshold_accuracy: float = 1.0,
    timeout_seconds: int = 180,
    config_file_path: str = None
) -> dict:
    """指定されたスキルに対してADK評価シミュレーションを実行し、その結果を検証します。

    Args:
        skill: 対象のスキル名。
        eval_set_path: 評価用のテストケースファイル (*.evalset.json) の相対パス。
        threshold_accuracy: 評価が合格するために必要な最小精度。デフォルトは 1.0。
        timeout_seconds: 評価タイムアウト秒数。デフォルトは 180。
        config_file_path: 評価設定ファイルのカスタムパス。

    Returns:
        検証結果（status, details, score）を含む辞書。
    """
    executor = SkillExecutor(
        skill=skill,
        eval_set_path=eval_set_path,
        threshold_accuracy=threshold_accuracy,
        timeout_seconds=timeout_seconds,
        config_file_path=config_file_path
    )
    result = executor.execute()
    return result.model_dump()
