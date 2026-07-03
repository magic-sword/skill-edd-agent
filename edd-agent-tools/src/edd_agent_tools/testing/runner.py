import os
import sys
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
        
        result = subprocess.run(cmd_args, **run_args)
        
        if result.returncode != 0:
            print(f"Subprocess '{self.command.skill_name}' failed with exit code {result.returncode}.", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            sys.exit(1)
            
        return result


class CommandLineRunner:
    """Command を現在のプロセス内で (CLI 起動として) 実行するランナー"""
    def __init__(self, command: Command):
        self.command = command

    def run(self, process_func):
        """引数のパース、状態のマージ、およびビジネスロジックの実行を行います。"""
        # 1. コマンドから実行用の引数 (args, kwargs) を構築 (多態的)
        try:
            exec_args, exec_kwargs = self.command.build_exec_args()
        except Exception as e:
            print(f"Error building command args: {e}", file=sys.stderr)
            sys.exit(1)
        
        # 2. 実行
        try:
            process_func(*exec_args, **exec_kwargs)
        except Exception as e:
            print(f"Error executing business logic: {e}", file=sys.stderr)
            if exec_args and hasattr(exec_args[0], 'state'):
                exec_args[0].state.update({
                    "status": "failed",
                    "message": str(e)
                })
                try:
                    self.command.handle_result(exec_args)
                except Exception as he:
                    print(f"Error handling failure result: {he}", file=sys.stderr)
            sys.exit(1)
            
        # 3. 結果の出力・永続化 (多態的)
        self.command.handle_result(exec_args)
