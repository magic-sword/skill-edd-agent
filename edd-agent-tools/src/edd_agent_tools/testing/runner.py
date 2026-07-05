import os
import sys
import subprocess
from typing import Tuple
from edd_agent_tools.models import EvalRunResult

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
        # 共通パッケージのインストールディレクトリから相対パスでパッチディレクトリを自動解決
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        patch_dir = os.path.join(current_file_dir, "patch")
        
        # edd-agent-tools の src ディレクトリのルートを特定
        edd_tools_src_dir = os.path.abspath(os.path.join(current_file_dir, "..", ".."))

        # ベース環境変数を構成
        patched_env = os.environ.copy()
        if env_vars:
            patched_env.update(env_vars)

        # PYTHONPATH を構成
        pythonpaths = [patch_dir, edd_tools_src_dir]
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        if current_pythonpath:
            # 既存の PYTHONPATH と重複しないように追加
            for path in current_pythonpath.split(":"):
                if path and path not in pythonpaths:
                    pythonpaths.append(path)
        patched_env["PYTHONPATH"] = ":".join(pythonpaths)

        # コマンドの組み立て (adk eval の代わりに eval_launcher スクリプトを Python 起動)
        cmd_args = [sys.executable, "-m", "edd_agent_tools.testing.eval_launcher", agent_dir, eval_set_path]
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
                # 失敗時、エラーログが出力されているはずなので、空の失敗結果を返すか、例外を投げる
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
