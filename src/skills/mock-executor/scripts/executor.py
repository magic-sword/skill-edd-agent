import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools import EvalRunResult, Skill

from .models import Input, Output
from .client import ADKEvalClient

class SkillExecutor:
    """
    ADK評価シミュレーションを実行し、その結果を検証するビジネスロジックを担うクラス。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context
        self._eval_client = ADKEvalClient()

    def execute(self) -> Output:
        """
        ADK評価シミュレーションを実行し、結果を検証します。
        """
        try:
            skill_name = self.params.skill
            if not skill_name:
                raise ValueError("エラー: 'skill' は必須です。")

            target_skill = self._get_skill_info(skill_name)
            
            # eval_set_path の解決 (paramsで指定がなければデフォルトのトリガー評価セットを使用)
            eval_set_path = self._resolve_eval_set_path(target_skill, self.params.eval_set_path)
            
            # config_file_path の解決と準備 (paramsで指定がなければ自動生成)
            config_file_path = self._resolve_and_prepare_eval_config(target_skill, eval_set_path, self.params.config_file_path)

            print(f"Running mock-executor for skill: {skill_name}")
            print(f"Eval set: {eval_set_path}")
            
            threshold_accuracy = self.params.threshold_accuracy if self.params.threshold_accuracy is not None else 1.0
            timeout_seconds = self.params.timeout_seconds if self.params.timeout_seconds is not None else 180
            print(f"Threshold accuracy: {threshold_accuracy:.4f}, Timeout: {timeout_seconds}s")

            eval_result = self._run_adk_eval(skill_name, eval_set_path, config_file_path, timeout_seconds)
            
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


    def _get_skill_info(self, skill_name: str) -> Skill:
        """スキル名からスキル情報を取得します。"""
        return self._eval_client.get_skill(skill_name)

    def _resolve_eval_set_path(self, target_skill: Skill, eval_set_path_param: str | None) -> str:
        """評価セットのパスを解決します。指定がない場合はデフォルトを使用します。"""
        if not eval_set_path_param:
            return target_skill.get_eval_set_path("trigger")
        return eval_set_path_param

    def _resolve_and_prepare_eval_config(self, target_skill: Skill, eval_set_path: str, config_file_path_param: str | None) -> str:
        """評価設定ファイルのパスを解決し、必要に応じて生成します。"""
        if config_file_path_param:
            # config_file_pathが明示的に指定された場合はそれを使用
            print(f"Using explicitly provided eval config file: {config_file_path_param}")
            return config_file_path_param
        else:
            # config_file_pathが指定されない場合は自動解決または生成
            config_file = self._eval_client.resolve_and_prepare_eval_config(target_skill, eval_set_path)
            print(f"Using auto-resolved eval config file: {config_file}")
            return config_file


    def _run_adk_eval(self, skill_name: str, eval_set_path: str, config_file_path: str, timeout_seconds: int) -> EvalRunResult:
        """ADK評価シミュレーションを実行します。"""
        env = {
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
            "SKILL": skill_name
        }
        # agent_dir は executor_old.py に合わせて暫定的に "/workspace/src/mock_entry" を使用。
        # 本来は評価対象スキルのルートディレクトリを指すべきであるため、将来的に改善の余地あり。
        return self._eval_client.run_eval(
            agent_dir="/workspace/src/mock_entry",
            eval_set_path=eval_set_path,
            config_file_path=config_file_path,
            timeout_seconds=timeout_seconds,
            env_vars=env
        )

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
