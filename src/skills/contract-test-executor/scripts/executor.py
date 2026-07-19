import json
from edd_agent_tools import WorkspaceEnvProtocol
from edd_agent_tools.skills import SkillsState
from edd_agent_tools.evaluation import ContractTestRunner, EvalCaseSet, EvalRunResult

class SkillExecutor:
    """指定されたスキルと評価セットパスに基づき、契約駆動のテストを実行し、その結果を返します。"""
    def __init__(self):
        self._skills_state = SkillsState()

    def run_tests(self, skill_name: str, eval_set_path: str, env: WorkspaceEnvProtocol) -> EvalRunResult:
        """指定されたスキルと評価セットパスに基づき、契約駆動のテストを実行し、その結果を返します。

        Args:
            skill_name: テストを実行する対象スキルの名前。
            eval_set_path: テストケースが記述されたEvalCaseSetフォーマットのJSONファイルへのパス。
            env: テスト実行環境。

        Returns:
            テスト実行結果オブジェクト (EvalRunResult)。
        """
        try:
            # 1. SkillsState から Skill オブジェクトを取得
            skill_obj = self._skills_state.get_skill(skill_name)
            
            # 2. テストケースのロードとパース
            with open(eval_set_path, "r", encoding="utf-8") as f:
                test_cases_data = json.load(f)
            eval_case_set = EvalCaseSet.model_validate(test_cases_data)

            # 3. ContractTestRunner を用いてテスト実行
            runner = ContractTestRunner()
            eval_run_result: EvalRunResult = runner.run_tests(
                skill=skill_obj, 
                test_cases_data=eval_case_set, 
                env=env
            )
            return eval_run_result

        except Exception as e:
            # エラー発生時はダミーの失敗結果を返す
            import traceback
            traceback.print_exc()
            return EvalRunResult(
                passed=0,
                failed=1,
                total=1,
                accuracy=0.0,
                detail_file_path=None
            )
