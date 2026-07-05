import os
import sys
import subprocess
from typing import Tuple

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
    ) -> Tuple[str, str, int]:
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

        # コマンドの組み立て
        cmd_args = ["adk", "eval", agent_dir, eval_set_path]
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
            return result.stdout or "", result.stderr or "", result.returncode
            
        except subprocess.TimeoutExpired as e:
            print(f"\n❌ エラー: テスト実行がタイムアウト（{timeout_seconds}秒）しました。デッドロック防止のため終了します。", file=sys.stderr)
            stdout_str = e.stdout or ""
            stderr_str = e.stderr or f"Timeout after {timeout_seconds} seconds."
            return stdout_str, stderr_str, 1
        except Exception as e:
            print(f"テスト実行中に予期せぬエラーが発生しました: {e}", file=sys.stderr)
            raise
