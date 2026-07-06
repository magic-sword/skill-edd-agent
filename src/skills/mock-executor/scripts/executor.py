import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools import EvalRunResult, SkillRegistry

from .models import Input, Output

class SkillExecutor:
    """
    ADK評価シミュレーションを実行し、その結果を検証するビジネスロジックを担うクラス。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context
        self._registry = SkillRegistry()

    def execute(self) -> Output:
        """
        ADK評価シミュレーションを実行し、結果を検証します。
        """
        try:
            skill_name = self.params.skill
            if not skill_name:
                raise ValueError("エラー: 'skill' は必須です。")

            target_skill = self._registry.get_skill(name=skill_name)
            
            eval_set_path = self.params.eval_set_path
            eval_obj = target_skill.get_eval(eval_set_path)

            print(f"Running mock-executor for skill: {skill_name}")
            print(f"Eval set: {eval_set_path}")
            
            threshold_accuracy = self.params.threshold_accuracy
            timeout_seconds = self.params.timeout_seconds
            print(f"Threshold accuracy: {threshold_accuracy:.4f}, Timeout: {timeout_seconds}s")

            # 評価の実行
            eval_result = eval_obj.execute(
                timeout_seconds=timeout_seconds,
                config_file_path=self.params.config_file_path
            )
            
            output_message = self._process_eval_result(eval_result, threshold_accuracy)

            return Output(value=output_message)

        except FileNotFoundError as e:
            self._update_state_on_error(f"ファイルが見つかりません: {e}", 0.0, self.params.threshold_accuracy or 1.0)
            print(f"エラー: {e}", file=sys.stderr)
            raise RuntimeError(f"ファイルが見つかりません: {e}")
        except ValueError as e:
            self._update_state_on_error(str(e), 0.0, self.params.threshold_accuracy or 1.0)
            print(f"エラー: {e}", file=sys.stderr)
            raise RuntimeError(str(e))
        except RuntimeError as e:
            # RuntimeErrorは_process_eval_resultでstateが更新されている可能性があるため、
            # stateがまだ更新されていなければ更新する
            if "status" not in self.tool_context.state:
                self._update_state_on_error(str(e), 0.0, self.params.threshold_accuracy or 1.0)
            print(f"エラー: {e}", file=sys.stderr)
            raise
        except Exception as e:
            self._update_state_on_error(f"予期せぬエラーが発生しました: {str(e)}", 0.0, self.params.threshold_accuracy or 1.0)
            print(f"予期せぬエラー: {e}", file=sys.stderr)
            raise RuntimeError(f"予期せぬエラーが発生しました: {str(e)}")

    def _process_eval_result(self, result: EvalRunResult, threshold_accuracy: float) -> str:
        """評価結果を解析し、合否判定とメッセージ生成、ToolContext.stateの更新を行います。"""
        accuracy = result.accuracy
        print(f"解析結果: 合格 = {result.passed}, 不合格 = {result.failed}, 合計 = {result.total}, 精度 = {accuracy:.4f}")

        status = "passed" if accuracy >= threshold_accuracy else "failed"
        message = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if status == 'passed' else 'less than'} threshold {threshold_accuracy:.4f}."
        if status == "failed" and result.detail_file_path:
            message += f"\n詳細な不合格理由は、以下の結果ファイルを参照してください：\n{result.detail_file_path}"
        
        self.tool_context.state.update({
            "status": status,
            "message": message,
            "accuracy": accuracy,
            "threshold_accuracy": threshold_accuracy
        })

        if status == "passed":
            print(f"\n🎉 テスト合格! 精度 {accuracy:.4f} >= 閾値 {threshold_accuracy:.4f}")
            return message
        else:
            print(f"\n❌ テスト不合格! 精度 {accuracy:.4f} < 閾値 {threshold_accuracy:.4f}", file=sys.stderr)
            raise RuntimeError(message)

    def _update_state_on_error(self, error_message: str, accuracy: float, threshold: float):
        """エラー発生時にtool_context.stateを更新します。"""
        self.tool_context.state.update({
            "status": "failed",
            "message": error_message,
            "accuracy": accuracy,
            "threshold_accuracy": threshold
        })
