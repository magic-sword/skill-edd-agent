from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.evaluation.models import EvalRunResult
from .executor import SkillExecutor

def run_tests(skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
    """指定されたスキルとゴールデンデータセットを用い、仮想環境上で意味的テストを実行・評価します。

    Args:
        skill_name: テスト対象のスキル名。
        eval_set_path: ゴールデンデータテストケースが記述されたJSONファイルの絶対パス。
        env: テストを実行するサンドボックス環境（WorkspaceEnvProtocol）。

    Returns:
        テスト実行結果オブジェクト (EvalRunResult)。
    """
    executor = SkillExecutor()
    return executor.run_tests(skill_name=skill_name, eval_set_path=eval_set_path, env=env)
