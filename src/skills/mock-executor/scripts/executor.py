import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools import EvalRunResult, SkillRegistry

from .models import Input, Output

class SkillExecutor:
    """ADK評価シミュレーションを実行し、その結果を検証します。

    このクラスは、指定されたスキルに対してADK評価シミュレーションを実行し、
    与えられた精度閾値に基づいて評価が合格したかを判断するビジネスロジックをカプセル化します。

    Attributes:
        params: スキル実行のための入力パラメータ。
        tool_context: 状態やその他のユーティリティへのアクセスを提供するツールコンテキスト。
        _registry: スキル定義にアクセスするための SkillRegistry インスタンス。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        """SkillExecutor を入力パラメータとツールコンテキストで初期化します。

        Args:
            params: スキルに提供される入力パラメータ。
            tool_context: スキル状態とインタラクションを管理するためのツールコンテキスト。
        """
        self.params = params
        self.tool_context = tool_context
        self._registry = SkillRegistry()

    def execute(self) -> Output:
        """ADK評価シミュレーションを実行し、その結果を検証します。

        このメソッドは、対象スキルの取得、評価セットの実行、
        そして定義された精度閾値に対する結果の処理を含む評価プロセスを統括します。

        Returns:
            評価結果メッセージを含む Output オブジェクト。

        Raises:
            ValueError: スキル名が提供されていない場合。
            FileNotFoundError: 指定された評価セットまたは設定ファイルが見つからない場合。
            RuntimeError: 評価中に予期せぬエラーが発生した場合、または評価が失敗した場合。
        """
        try:
            skill_name = self.params.skill
            if not skill_name:
                raise ValueError("'skill' parameter is required.")

            target_skill = self._registry.get_skill(name=skill_name)
            
            eval_set_path = self.params.eval_set_path
            eval_obj = target_skill.get_eval(eval_set_path)

            print(f"Running mock-executor for skill: {skill_name}")
            print(f"Eval set: {eval_set_path}")
            
            threshold_accuracy = self.params.threshold_accuracy
            timeout_seconds = self.params.timeout_seconds
            print(f"Threshold accuracy: {threshold_accuracy:.4f}, Timeout: {timeout_seconds}s")

            eval_result = eval_obj.execute(
                timeout_seconds=timeout_seconds,
                config_file_path=self.params.config_file_path
            )
            
            output_message = self._process_eval_result(eval_result, threshold_accuracy)

            return Output(value=output_message)

        except FileNotFoundError as e:
            error_message = f"File not found: {e}"
            self._update_state_on_error(error_message, 0.0, self.params.threshold_accuracy or 1.0)
            print(f"Error: {error_message}", file=sys.stderr)
            raise RuntimeError(error_message) from e
        except ValueError as e:
            error_message = str(e)
            self._update_state_on_error(error_message, 0.0, self.params.threshold_accuracy or 1.0)
            print(f"Error: {error_message}", file=sys.stderr)
            raise RuntimeError(error_message) from e
        except RuntimeError as e:
            error_message = str(e)
            if "status" not in self.tool_context.state:
                self._update_state_on_error(error_message, 0.0, self.params.threshold_accuracy or 1.0)
            print(f"Error: {error_message}", file=sys.stderr)
            raise
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            self._update_state_on_error(error_message, 0.0, self.params.threshold_accuracy or 1.0)
            print(f"Unexpected error: {error_message}", file=sys.stderr)
            raise RuntimeError(error_message) from e

    def _process_eval_result(self, result: EvalRunResult, threshold_accuracy: float) -> str:
        """評価結果を処理し、合否を判断してメッセージを生成し、`ToolContext.state` を更新します。

        Args:
            result: 生の評価結果を含む `EvalRunResult` オブジェクト。
            threshold_accuracy: 評価が合格するために必要な最小精度。

        Returns:
            評価結果を要約する文字列メッセージ。

        Raises:
            RuntimeError: 評価結果が失敗を示している場合。
        """
        accuracy = result.accuracy
        print(f"Evaluation result: Passed = {result.passed}, Failed = {result.failed}, Total = {result.total}, Accuracy = {accuracy:.4f}")

        status = "passed" if accuracy >= threshold_accuracy else "failed"
        message = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if status == 'passed' else 'less than'} threshold {threshold_accuracy:.4f}."
        if status == "failed" and result.detail_file_path:
            message += f"\nFor detailed failure reasons, please refer to the result file:\n{result.detail_file_path}"
        
        self.tool_context.state.update({
            "status": status,
            "message": message,
            "accuracy": accuracy,
            "threshold_accuracy": threshold_accuracy
        })

        if status == "passed":
            print(f"\n🎉 Test passed! Accuracy {accuracy:.4f} >= Threshold {threshold_accuracy:.4f}")
            return message
        else:
            print(f"\n❌ Test failed! Accuracy {accuracy:.4f} < Threshold {threshold_accuracy:.4f}", file=sys.stderr)
            raise RuntimeError(message)

    def _update_state_on_error(self, error_message: str, accuracy: float, threshold: float):
        """評価中にエラーが発生した場合に `tool_context.state` を更新します。

        Args:
            error_message: 状態に格納されるエラーメッセージ。
            accuracy: 記録される精度値（エラー時は通常 0.0）。
            threshold: 評価が実行された際の閾値精度。
        """
        self.tool_context.state.update({
            "status": "failed",
            "message": error_message,
            "accuracy": accuracy,
            "threshold_accuracy": threshold
        })
