"""
first-test-runner スキルの主要なビジネスロジックを定義するモジュール。
"""

from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState, Skill

from .models import RunFirstTestOutput
from .exceptions import TestFailedError
from .test_runner_client import TestRunnerClient
from .skill_state_client import SkillStateClient

class SkillExecutor:
    """指定されたスキルに対して一連のテストと検証を実行し、すべて成功した場合はスキルをTier 1として登録するワークフロー。"""

    def __init__(
        self,
        tool_context: ToolContext,
        skills_state: SkillsState,
        test_runner_client: TestRunnerClient,
        skill_state_client: SkillStateClient,
    ):
        """
        SkillExecutorのコンストラクタ。

        Args:
            tool_context: ToolContextインスタンス。
            skills_state: SkillsStateインスタンス。
            test_runner_client: TestRunnerClientインスタンス。
            skill_state_client: SkillStateClientインスタンス。
        """
        self._tool_context = tool_context
        self._skills_state = skills_state
        self._test_runner_client = test_runner_client
        self._skill_state_client = skill_state_client

    def run_first_test(self, skill: str) -> RunFirstTestOutput:
        """
        指定されたスキルに対して一連のテストと検証を実行し、すべて成功した場合はスキルをTier 1として登録します。

        Args:
            skill: 試験対象のスキル名。

        Returns:
            実行結果オブジェクト (RunFirstTestOutput)。
        
        Raises:
            TestFailedError: テスト実行が失敗した場合。
        """
        try:
            # 0. 依存関係の動的整合性検証（欠落・循環参照）
            try:
                self._skills_state.validate_dependencies()
            except ValueError as ve:
                raise TestFailedError(str(ve))

            # 1. trigger_check
            trigger_result = self._test_runner_client.run_test(
                skill_name=skill,
                test_type="trigger",
                threshold_accuracy=0.9,
            )
            if trigger_result.get("status") != "success":
                raise TestFailedError(f"Triggerテストが失敗しました: {trigger_result.get('message', '不明なエラー')}")

            # 2. contract_check
            contract_result = self._test_runner_client.run_test(
                skill_name=skill,
                test_type="contract",
                threshold_accuracy=1.0,
            )
            if contract_result.get("status") != "success":
                raise TestFailedError(f"Contractテストが失敗しました: {contract_result.get('message', '不明なエラー')}")

            # 3. register_skill
            skill_obj = self._skills_state.get_skill(skill)
            if not skill_obj:
                raise TestFailedError(f"スキル '{skill}' がSkillsStateに見つかりませんでした。")

            self._skill_state_client.register_skill_as_tier1(skill_obj)

            return RunFirstTestOutput(
                status="success",
                message="すべてのテストと検証が成功し、スキルがTier 1として登録されました。",
                registered=True,
            )

        except TestFailedError as e:
            return RunFirstTestOutput(
                status="failed",
                message=str(e),
                registered=False,
            )
        except Exception as e:
            return RunFirstTestOutput(
                status="failed",
                message=f"予期せぬエラーが発生しました: {str(e)}",
                registered=False,
            )
