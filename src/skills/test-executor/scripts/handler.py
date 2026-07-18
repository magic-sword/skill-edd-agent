from .models import ExecuteAdkSimulationOutput
from .executor import SkillExecutor

def execute_adk_simulation(skill: str, eval_set_path: str, test_type: str, threshold_accuracy: float = 1.0) -> ExecuteAdkSimulationOutput:
    """ADK評価シミュレーションを実行し、指定されたスキルの動作を検証します。

    Args:
        skill: 評価対象スキルの名前。
        eval_set_path: 評価用のテストケースファイル (*.evalset.json) のパス。
        test_type: テストケースの種別（例: 'trigger', 'unit'）。
        threshold_accuracy: 評価が合格するために必要な最小精度。

    Returns:
        実行結果オブジェクト (ExecuteAdkSimulationOutput)。
    """
    executor = SkillExecutor(
        skill=skill, 
        eval_set_path=eval_set_path, 
        test_type=test_type, 
        threshold_accuracy=threshold_accuracy
    )
    return executor.execute()


