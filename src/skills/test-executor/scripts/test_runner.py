import subprocess
import os
import sys
from typing import Tuple

class TestRunner:
    def run_adk_eval(
        self,
        skill: str,
        eval_set_path: str,
        config_file_path: str,
        timeout_seconds: int,
        cwd: str = "/workspace"
    ) -> Tuple[str, str, int]:
        """
        adk eval コマンドをサブプロセスとして実行します。
        """
        print(f"Running test-executor for skill: {skill}")
        print(f"Eval set: {eval_set_path}")
        print(f"Threshold accuracy: (handled by logic.py), Timeout: {timeout_seconds}s")

        # adk evalの環境変数の設定
        env = {
            "HOME": "/home/vscode",
            "PATH": os.environ.get("PATH", "/workspace/.venv/bin:/usr/local/bin:/usr/bin:/bin"),
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
            "SKILL": skill
        }
        
        # 評価エンジンのための多言語パッチ環境変数の構成
        patched_env = os.environ.copy() if env is None else env.copy() # envがNoneの場合はos.environ.copy()を使用
        if env: # envが指定されている場合は、patched_envにマージする
            patched_env.update(env)

        patch_dir = os.path.abspath(os.path.join("/workspace/edd-agent-tools/src/edd_agent_tools/testing/patch"))
        current_pythonpath = patched_env.get("PYTHONPATH", "")
        if current_pythonpath:
            patched_env["PYTHONPATH"] = f"{patch_dir}:{current_pythonpath}"
        else:
            patched_env["PYTHONPATH"] = patch_dir
            
        edd_tools_path = os.path.abspath("/workspace/edd-agent-tools/src")
        patched_env["PYTHONPATH"] = f"{edd_tools_path}:{patched_env['PYTHONPATH']}"

        # SystemCommand の引数リストを定義
        args = ["eval", "/workspace/src", eval_set_path]
        if config_file_path:
            args.extend(["--config_file_path", config_file_path])
        
        cmd_args = ["adk"] + args
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
            # 結果の表示
            print("--- ADK EVAL OUTPUT ---")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            print("-----------------------")

            return result.stdout or "", result.stderr or "", result.returncode
            
        except subprocess.TimeoutExpired as e:
            print(f"\n❌ エラー: テスト実行がタイムアウト（{timeout_seconds}秒）しました。デッドロック防止のため終了します。", file=sys.stderr)
            if e.stdout:
                print(f"STDOUT:\n{e.stdout}", file=sys.stderr)
            if e.stderr:
                print(f"STDERR:\n{e.stderr}", file=sys.stderr)
            raise RuntimeError(f"Timeout after {timeout_seconds} seconds.") from e
        except Exception as e:
            print(f"テスト実行中に予期せぬエラーが発生しました: {e}", file=sys.stderr)
            raise