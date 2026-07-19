"""
test-generator および test-executor スキルをインプロセスで呼び出すクライアントモジュール。
"""

from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState

class TestRunnerClient:
    """
    test-generator と test-executor スキルを介してテストを実行するクライアント。
    """
    def __init__(self, tool_context: ToolContext):
        """
        TestRunnerClientのコンストラクタ。

        Args:
            tool_context: ToolContextインスタンス。
        """
        self._tool_context = tool_context
        self._state = SkillsState()

    def run_test(self, skill_name: str, test_type: str, threshold_accuracy: float) -> dict:
        """
        指定されたスキルに対してテストケースを生成し、実行して精度評価結果を返す。

        Args:
            skill_name: 試験対象のスキル名。
            test_type: テストのタイプ（"trigger" または "schema"）。
            threshold_accuracy: 合格判定の閾値。

        Returns:
            テスト実行結果を表す辞書。
        """
        try:
            # 1. test-generator スキルを動的ロード
            generator_skill = self._state.get_skill("test-generator")
            generator_module = generator_skill.load_module()
            
            gen_result = generator_module.generate_test_cases(
                skill=skill_name,
                test_type=test_type
            )
            
            if gen_result.status != "success":
                return {
                    "status": "failed",
                    "message": f"{test_type}テストケース生成失敗: {gen_result.message}"
                }

            eval_set_path = gen_result.eval_set_path

            # 2. test-executor スキルを動的ロード
            executor_skill = self._state.get_skill("test-executor")
            executor_module = executor_skill.load_module()

            exec_result = executor_module.execute_adk_simulation(
                skill=skill_name,
                eval_set_path=eval_set_path,
                test_type=test_type,
                threshold_accuracy=threshold_accuracy
            )

            if exec_result.status != "success":
                return {
                    "status": "failed",
                    "message": f"{test_type}テスト実行不合格: {exec_result.details}",
                    "score": exec_result.score
                }

            # 閾値精度チェック
            if exec_result.score < threshold_accuracy:
                return {
                    "status": "failed",
                    "message": f"{test_type}精度 ({exec_result.score:.2f}) が閾値 ({threshold_accuracy:.2f}) 未満です。: {exec_result.details}",
                    "score": exec_result.score
                }

            return {
                "status": "success",
                "message": f"{test_type}テストが合格しました。精度: {exec_result.score:.2f}",
                "score": exec_result.score
            }

        except Exception as e:
            return {
                "status": "failed",
                "message": f"{test_type}テスト実行中に予期せぬエラーが発生しました: {e}"
            }
