from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.evaluation.models import EvalRunResult
from .executor import SkillExecutor

def run_tests(skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
    """敵対的・限界テストを実行し、結果(EvalRunResult)を返します。

    Args:
        skill_name: テスト実行対象のスキル名。
        eval_set_path: テストケースが記述されたEvalCaseSetフォーマットのJSONファイルへのパス。
        env: テスト実行環境。

    Returns:
        テスト実行結果オブジェクト (EvalRunResult)。
    """
    executor = SkillExecutor()
    return executor.run_tests(skill_name=skill_name, eval_set_path=eval_set_path, env=env)
