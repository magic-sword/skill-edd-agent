"""
test-generator および test-executor スキルを呼び出すためのクライアントモジュール。
"""

from google.adk.tools import ToolContext

class TestRunnerClient:
    """
    test-generator と test-executor スキルを介してテストを実行するクライアント。
    """
    def __init__(self, tool_context: ToolContext):
        """
        TestRunnerClientのコンストラクタ。

        Args:
            tool_context: ToolContextインスタンス。スキル実行のために必要。
        """
        self._tool_context = tool_context

    def run_test(self, skill_name: str, test_type: str, threshold_accuracy: float) -> dict:
        """
        指定されたスキルに対してテストケースを生成し、実行する。

        Args:
            skill_name: テスト対象のスキル名。
            test_type: テストのタイプ（例: "trigger", "schema"）。
            threshold_accuracy: 合格判定の閾値。

        Returns:
            テスト実行結果の辞書。
        """
        # test-generator スキルを呼び出してテストケースを生成
        generate_output = self._tool_context.run_skill(
            skill_id="test-generator",
            function_name="generate_test_cases",
            parameters={
                "skill_name": skill_name,
                "test_type": test_type
            }
        )

        test_cases = generate_output.get("test_cases")
        if not test_cases:
            return {"status": "failed", "message": f"テストケースの生成に失敗しました: {generate_output.get('message', '不明なエラー')}"}

        # test-executor スキルを呼び出してテストケースを実行
        execute_output = self._tool_context.run_skill(
            skill_id="test-executor",
            function_name="execute_test_cases",
            parameters={
                "skill_name": skill_name,
                "test_cases": test_cases,
                "threshold_accuracy": threshold_accuracy
            }
        )

        return execute_output
