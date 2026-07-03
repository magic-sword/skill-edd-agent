import os
import subprocess
from edd_agent_tools.testing.command import Command

def _get_patched_env(base_env: dict = None) -> dict:
    """ADK 評価エンジンで日本語などの多言語トークナイズを有効にするためのパッチ済みの環境変数を取得します。"""
    if base_env is None:
        base_env = os.environ.copy()
        
    # patch ディレクトリの絶対パスを解決
    patch_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "patch"))
    
    # PYTHONPATH に追加する
    current_pythonpath = base_env.get("PYTHONPATH", "")
    if current_pythonpath:
        base_env["PYTHONPATH"] = f"{patch_dir}:{current_pythonpath}"
    else:
        base_env["PYTHONPATH"] = patch_dir
    return base_env


class SubprocessRunner:
    """多言語パッチを自動適用した状態でコマンドをサブプロセスとして実行するランナー"""
    def __init__(self, command: Command):
        self.command = command

    def run(self, env: dict = None, **kwargs) -> subprocess.CompletedProcess:
        """保持しているコマンドを安全に実行します。"""
        cmd_args = self.command.build_cmd_args()
        patched_env = _get_patched_env(env)
        
        run_args = {
            "env": patched_env,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "cwd": "/workspace"
        }
        run_args.update(kwargs)
        return subprocess.run(cmd_args, **run_args)
