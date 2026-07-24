from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.evaluation.models import EvalRunResult
from .executor import TrajectoryTestExecutor

def run_tests(skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
    """指定されたスキルと TrajectoryEvalSet ファイルに基づき、決定論的なツール軌跡テストを実行します。

    Args:
        skill_name: テスト対象スキルの名前。
        eval_set_path: TrajectoryEvalSet 形式の JSON ファイルへのパス。
        env: サンドボックス環境。

    Returns:
        EvalRunResult オブジェクト。
    """
    executor = TrajectoryTestExecutor()
    return executor.run_tests(skill_name=skill_name, eval_set_path=eval_set_path, env=env)
