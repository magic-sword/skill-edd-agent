import json
from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.evaluation import ContractTestRunner, EvalCaseSet, EvalRunResult

class SkillExecutor:
    """指定されたスキルと敵対的・限界テストセットに基づき、テストを実行して結果(EvalRunResult)を返します。"""
    def __init__(self):
        self._skills_state = SkillsState()

    def run_tests(self, skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
        """指定されたスキルと評価セットパスに基づき、敵対的・限界テストを実行します。

        Args:
            skill_name: テスト対象のスキル名。
            eval_set_path: EvalCaseSetフォーマットのJSONファイルパス。
            env: サンドボックス環境。

        Returns:
            EvalRunResult オブジェクト。
        """
        try:
            skill_obj = self._skills_state.get_skill(skill_name)
            with open(eval_set_path, "r", encoding="utf-8") as f:
                test_cases_data = json.load(f)
            eval_case_set = EvalCaseSet.model_validate(test_cases_data)

            runner = ContractTestRunner()
            eval_run_result: EvalRunResult = runner.run_tests(
                skill=skill_obj,
                test_cases_data=eval_case_set,
                env=env
            )
            return eval_run_result

        except Exception as e:
            import traceback
            traceback.print_exc()
            return EvalRunResult(
                passed=0,
                failed=1,
                total=1,
                accuracy=0.0,
                detail_file_path=None
            )
