from .models import ExecuteAdkSimulationOutput
from .executor import SkillExecutor

def execute_adk_simulation(skill: str, eval_set_path: str, threshold_accuracy: float = '1.0', timeout_seconds: int = '180', config_file_path: str | None = None) -> ExecuteAdkSimulationOutput:
    """ADK評価シミュレーションを実行し、指定されたスキルの動作を検証します。

    Args:
        skill: 評価対象スキルの名前。
        eval_set_path: 評価用のテストケースファイル (*.evalset.json) のパス。
        threshold_accuracy: 評価が合格するために必要な最小精度。
        timeout_seconds: 評価タイムアウト秒数。
        config_file_path: 評価設定ファイルのカスタムパス。

    Returns:
        実行結果オブジェクト (ExecuteAdkSimulationOutput)。
    """
    executor = SkillExecutor()
    return executor.execute_adk_simulation(skill=skill, eval_set_path=eval_set_path, threshold_accuracy=threshold_accuracy, timeout_seconds=timeout_seconds, config_file_path=config_file_path)

