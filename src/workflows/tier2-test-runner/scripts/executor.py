"""
tier2-test-runner スキルの主要なビジネスロジックを定義するモジュール。
"""

from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState, Skill

from .models import RunTier2TestOutput
from .exceptions import TestFailedError
from .test_runner_client import TestRunnerClient
from .skill_state_client import SkillStateClient

class SkillExecutor:
    """指定されたスキルに対して contract, golden, judge テストを順次実行し、すべて合格した場合はスキルをTier 2 (Draft-Only)として登録するワークフロー。"""

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

    def run_tier2_test(self, skill: str) -> RunTier2TestOutput:
        """
        指定されたスキルに対して contract, golden, judge テストを実行し、すべて成功した場合はスキルをTier 2として登録します。

        Args:
            skill: 検証および昇格対象のスキル名。

        Returns:
            実行結果オブジェクト (RunTier2TestOutput)。
        """
        try:
            # 0. 依存関係の動的整合性検証（欠落・循環参照）
            try:
                self._skills_state.validate_dependencies()
            except ValueError as ve:
                raise TestFailedError(str(ve))

            # 1. contract_check (契約・型仕様テスト)
            contract_result = self._test_runner_client.run_test(
                skill_name=skill,
                test_type="contract",
                threshold_accuracy=1.0,
            )
            if contract_result.get("status") != "success":
                raise TestFailedError(f"Contractテストが不合格です: {contract_result.get('message', '不明なエラー')}")

            # 2. golden_check (ゴールデンテスト)
            golden_result = self._test_runner_client.run_test(
                skill_name=skill,
                test_type="golden",
                threshold_accuracy=1.0,
            )
            if golden_result.get("status") != "success":
                raise TestFailedError(f"Goldenテストが不合格です: {golden_result.get('message', '不明なエラー')}")

            # 3. judge_check (ルーブリックジャッジテスト)
            judge_result = self._test_runner_client.run_test(
                skill_name=skill,
                test_type="judge",
                threshold_accuracy=1.0,
            )
            if judge_result.get("status") != "success":
                raise TestFailedError(f"Judgeテストが不合格です: {judge_result.get('message', '不明なエラー')}")

            # 4. register_skill (Tier 2 昇格登録)
            skill_obj = self._skills_state.get_skill(skill)
            if not skill_obj:
                raise TestFailedError(f"スキル '{skill}' がSkillsStateに見つかりませんでした。")

            self._skill_state_client.register_skill_as_tier2(skill_obj)

            return RunTier2TestOutput(
                status="success",
                message="すべての検証テスト（contract, golden, judge）が100%合格し、スキルがTier 2 (Draft-Only) として登録されました。",
                registered=True,
            )

        except TestFailedError as e:
            return RunTier2TestOutput(
                status="failed",
                message=str(e),
                registered=False,
            )
        except Exception as e:
            return RunTier2TestOutput(
                status="failed",
                message=f"予期せぬエラーが発生しました: {str(e)}",
                registered=False,
            )
