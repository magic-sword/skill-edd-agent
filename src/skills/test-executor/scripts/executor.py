from edd_agent_tools.skills import SkillsState
from edd_agent_tools.evaluation import LocalWorkspaceEnv
from .models import ExecuteAdkSimulationOutput

class SkillExecutor:
    """ADK評価を実行し、その結果を検証する動的ディスパッチャー。"""
    def __init__(self, skill: str, eval_set_path: str, test_type: str, threshold_accuracy: float = 1.0):
        self.skill = skill
        self.eval_set_path = eval_set_path
        self.test_type = test_type
        self.threshold_accuracy = threshold_accuracy
        self._skills_state = SkillsState()

    def execute(self) -> ExecuteAdkSimulationOutput:
        """指定されたテストタイプに対応する Executor スキルを動的ロードして実行を委譲します。"""
        try:
            # 1. 対応するテスト実行スキルを動的ロード
            # 例: test_type="trigger" -> "trigger-test-executor"
            executor_skill_name = f"{self.test_type}-test-executor"
            executor_skill = self._skills_state.get_skill(executor_skill_name)
            executor_module = executor_skill.load_module()

            # 2. 共通インターフェース関数の存在チェック
            # プロトコル: run_tests(skill_name, eval_set_path, env) -> EvalRunResult
            if not hasattr(executor_module, "run_tests"):
                return ExecuteAdkSimulationOutput(
                    status="failed",
                    details=f"エラー: スキル '{executor_skill_name}' に 'run_tests' 関数が定義されていません。",
                    score=0.0
                )

            # 3. 隔離環境（サンドボックス）を構築して実行に移譲
            env = LocalWorkspaceEnv(
                workspace_dir=str(self._skills_state.project_root),
                use_git=True,
                use_host_venv=True
            )
            try:
                env.reset()
                eval_result = executor_module.run_tests(
                    skill_name=self.skill,
                    eval_set_path=self.eval_set_path,
                    env=env
                )
            finally:
                env.close()

            # 4. 実行結果の評価と返却
            accuracy = eval_result.accuracy
            is_passed = accuracy >= self.threshold_accuracy
            status = 'success' if is_passed else 'failed'
            details = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if is_passed else 'less than'} threshold {self.threshold_accuracy:.4f}."
            if not is_passed and eval_result.detail_file_path:
                details += f"\nFor details, see result file: {eval_result.detail_file_path}"

            return ExecuteAdkSimulationOutput(
                status=status,
                details=details,
                score=accuracy,
                detail_file_path=eval_result.detail_file_path
            )

        except Exception as e:
            return ExecuteAdkSimulationOutput(
                status="failed",
                details=f"予期せぬエラーが発生しました: {e}",
                score=0.0
            )
