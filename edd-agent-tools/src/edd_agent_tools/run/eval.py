import os
import sys
import subprocess
from edd_agent_tools.models import EvalRunResult
from edd_agent_tools.run.env import get_patched_env

class ADKEvalRunner:
    """
    ADK eval コマンドを実行し、必要な多言語パッチ用 PYTHONPATH などの環境変数を
    一元的に構成して安全に実行する共通ヘルパークラス。
    """
    @staticmethod
    def run_eval(
        agent_dir: str,
        eval_set_path: str,
        config_file_path: str,
        timeout_seconds: int,
        env_vars: dict = None,
        cwd: str = "/workspace"
    ) -> EvalRunResult:
        # env.py を使って環境変数を構成
        patched_env = get_patched_env(env_vars)

        # コマンドの組み立て (adk eval の代わりに launcher スクリプトを Python 起動)
        cmd_args = [sys.executable, "-m", "edd_agent_tools.run.launcher", agent_dir, eval_set_path]
        if config_file_path:
            cmd_args.extend(["--config_file_path", config_file_path])
            
        print(f"Executing: {' '.join(cmd_args)}")

        try:
            result = subprocess.run(
                cmd_args,
                env=patched_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
                cwd=cwd
            )
            if result.returncode == 0:
                return EvalRunResult.model_validate_json(result.stdout)
            else:
                print(f"Error during eval run (exit code {result.returncode}):\n{result.stderr}", file=sys.stderr)
                return EvalRunResult(
                    passed=0,
                    failed=1,
                    total=1,
                    accuracy=0.0,
                    detail_file_path=None
                )
            
        except subprocess.TimeoutExpired as e:
            print(f"\n❌ エラー: テスト実行がタイムアウト（{timeout_seconds}秒）しました。デッドロック防止のため終了します。", file=sys.stderr)
            return EvalRunResult(
                passed=0,
                failed=1,
                total=1,
                accuracy=0.0,
                detail_file_path=None
            )
        except Exception as e:
            print(f"テスト実行中に予期せぬエラーが発生しました: {e}", file=sys.stderr)
            raise
