from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.evaluation import EvalRunResult
from .executor import SkillExecutor

def run_tests(skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
    """トリガー（インテント）評価テストを実行し、その結果を検証します。

    Args:
        skill_name: 評価対象となるスキルの名前。
        eval_set_path: TrajectoryEvalSet形式 of JSONファイルへのパス。
        env: ワークスペース環境プロトコル。

    Returns:
        テスト実行結果オブジェクト (EvalRunResult)。
    """
    executor = SkillExecutor()
    return executor.run_tests(skill_name=skill_name, eval_set_path=eval_set_path, env=env)
