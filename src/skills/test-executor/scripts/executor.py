import os
import sys
from edd_agent_tools import EvalRunResult, SkillsState

from .models import Output

class SkillExecutor:
    """ADK評価シミュレーションを実行し、その結果を検証します。

    このクラスは、指定されたスキルに対してADK評価シミュレーションを実行し、
    与えられた精度閾値に基づいて評価が合格したかを判断するビジネスロジックをカプセル化します。
    """
    def __init__(self, skill: str, eval_set_path: str, threshold_accuracy: float = 1.0, timeout_seconds: int = 180, config_file_path: str = None):
        """SkillExecutor を入力パラメータで初期化します。

        Args:
            skill: 対象のスキル名。
            eval_set_path: 評価用のテストケースファイル (*.evalset.json) のパス。
            threshold_accuracy: 評価が合格するために必要な最小精度。
            timeout_seconds: 評価タイムアウト秒数。
            config_file_path: 評価設定ファイルのカスタムパス。
        """
        self.skill = skill
        self.eval_set_path = eval_set_path
        self.threshold_accuracy = threshold_accuracy
        self.timeout_seconds = timeout_seconds
        self.config_file_path = config_file_path
        self._state = SkillsState()

    def execute(self) -> Output:
        """ADK評価シミュレーションを実行し、その結果を検証します。

        Returns:
            評価結果メッセージを含む Output オブジェクト。
        """
        try:
            skill_name = self.skill
            if not skill_name:
                raise ValueError("'skill' parameter is required.")

            target_skill = self._state.get_skill(skill_name)
            eval_obj = target_skill.get_eval()

            print(f"Running simulation-executor for skill: {skill_name}")
            print(f"Eval set: {self.eval_set_path}")
            
            threshold_accuracy = self.threshold_accuracy
            timeout_seconds = self.timeout_seconds
            print(f"Threshold accuracy: {threshold_accuracy:.4f}, Timeout: {timeout_seconds}s")

            # 評価設定ファイルの準備
            config_path = self.config_file_path if self.config_file_path else eval_obj.prepare_config()
            with open(config_path, "r", encoding="utf-8") as f:
                import json
                config_data = json.load(f)
            
            max_steps = config_data.get("max_steps", 15)
            initial_prompt = config_data.get("initial_prompt", "目標に向かって行動してください。")

            # 環境を明示的に構築・破棄してシミュレーションを実行 (関心の分離)
            from edd_agent_tools.evaluation import LocalWorkspaceEnv
            env = LocalWorkspaceEnv(
                workspace_dir="/workspace",
                use_git=True,
                use_host_venv=True
            )
            try:
                env.reset()
                eval_result = eval_obj.execute_simulation(
                    env=env,
                    max_steps=max_steps,
                    initial_prompt=initial_prompt
                )
            finally:
                env.close()
            
            output_message, is_passed, accuracy = self._process_eval_result(eval_result, threshold_accuracy)
            status = 'success' if is_passed else 'failed'

            return Output(status=status, details=output_message, score=accuracy)

        except FileNotFoundError as e:
            error_message = f"File not found: {e}"
            print(f"Error: {error_message}", file=sys.stderr)
            return Output(status='failed', details=error_message, score=0.0)
        except ValueError as e:
            error_message = str(e)
            print(f"Error: {error_message}", file=sys.stderr)
            return Output(status='failed', details=error_message, score=0.0)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            print(f"Unexpected error: {error_message}", file=sys.stderr)
            return Output(status='failed', details=error_message, score=0.0)

    def _process_eval_result(self, result: EvalRunResult, threshold_accuracy: float) -> tuple[str, bool, float]:
        """評価結果を処理し、合否を判断してメッセージを生成します。

        Args:
            result: 生の評価結果を含む `EvalRunResult` オブジェクト。
            threshold_accuracy: 評価が合格するために必要な最小精度。

        Returns:
            評価結果を要約する文字列メッセージ、合否（True/False）、および測定された精度のタプル。
        """
        accuracy = result.accuracy
        print(f"Evaluation result: Passed = {result.passed}, Failed = {result.failed}, Total = {result.total}, Accuracy = {accuracy:.4f}")

        is_passed = accuracy >= threshold_accuracy
        status = "passed" if is_passed else "failed"
        message = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if status == 'passed' else 'less than'} threshold {threshold_accuracy:.4f}."
        if not is_passed and result.detail_file_path:
            message += f"\nFor detailed failure reasons, please refer to the result file:\n{result.detail_file_path}"
        
        if is_passed:
            print(f"\n🎉 Test passed! Accuracy {accuracy:.4f} >= Threshold {threshold_accuracy:.4f}")
        else:
            print(f"\n❌ Test failed! Accuracy {accuracy:.4f} < Threshold {threshold_accuracy:.4f}", file=sys.stderr)
        
        return message, is_passed, accuracy
