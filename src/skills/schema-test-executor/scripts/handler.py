from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.evaluation import EvalRunResult
from .executor import SkillExecutor

def run_tests(skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
    """指定されたスキルと評価セットパスに基づき、スキーマ駆動の単体テストを実行し、その結果を返します。

    Args:
        skill_name: テストを実行する対象スキルの名前。
        eval_set_path: テストケースが記述されたEvalCaseSetフォーマットのJSONファイルへのパス。
        env: テスト実行環境。

    Returns:
        テスト実行結果オブジェクト (EvalRunResult)。
    """
    executor = SkillExecutor()
    return executor.run_tests(skill_name=skill_name, eval_set_path=eval_set_path, env=env)
