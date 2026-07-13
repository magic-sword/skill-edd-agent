import os
import shutil
import tempfile
import subprocess
from typing import Dict, List, Any
from .models import WorkspaceArtifacts

class GitSandbox:
    """
    一時ディレクトリ（サンドボックス）でファイル操作およびGitステート制御を行うクラス。
    """
    def __init__(self, workspace_dir: str, target_files: List[str] = None, use_git: bool = True):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.target_files = target_files or []
        self.use_git = use_git
        self.sandbox_dir = None

    def create(self):
        """OSの一時領域にサンドボックス用の一時フォルダを作成し、本番ファイルを同期します。"""
        self.cleanup()
        self.sandbox_dir = tempfile.mkdtemp(prefix="edd_sandbox_")
        self._provision_sandbox()
        if self.use_git:
            self._init_git_repository()

    def cleanup(self):
        """一時フォルダ（サンドボックス）を物理消去します。"""
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            try:
                shutil.rmtree(self.sandbox_dir)
            except Exception:
                pass
        self.sandbox_dir = None

    def run_git(self, args: List[str]) -> subprocess.CompletedProcess:
        """混同を防ぐために --git-dir と --work-tree を強制して Git コマンドを実行します。"""
        if not self.sandbox_dir:
            raise RuntimeError("Sandbox is not initialized.")
            
        git_dir = os.path.join(self.sandbox_dir, ".git")
        work_tree = self.sandbox_dir
        
        full_cmd = [
            "git", 
            "--git-dir", git_dir, 
            "--work-tree", work_tree
        ] + args
        
        env = os.environ.copy()
        env.pop("GIT_DIR", None)
        env.pop("GIT_WORK_TREE", None)
        
        return subprocess.run(full_cmd, cwd=self.sandbox_dir, capture_output=True, text=True, env=env)

    def resolve_path(self, path: str) -> str:
        """指定された相対パスが一時サンドボックスの外部に出ていないか検証し、絶対パスを返します。"""
        if not self.sandbox_dir:
            raise RuntimeError("Sandbox is not initialized.")
        abs_path = os.path.abspath(os.path.join(self.sandbox_dir, path))
        if not abs_path.startswith(self.sandbox_dir):
            raise PermissionError(f"Access to path outside sandbox is restricted: {path}")
        return abs_path

    def get_artifacts(self) -> WorkspaceArtifacts:
        """初期状態からのファイル変更差分を抽出します。"""
        modified_files = {}
        deleted_files = []

        if not self.sandbox_dir:
            return WorkspaceArtifacts()

        if self.use_git:
            # 1. git status --porcelain -z を用いて、変更されたファイルを特定
            result = self.run_git(["status", "--porcelain", "-z"])
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.split('\0')
                for line in lines:
                    if not line:
                        continue
                    status = line[:2]
                    rel_path = line[3:]
                    
                    # 削除されたファイル
                    if 'D' in status:
                        deleted_files.append(rel_path)
                    # 修正、または新規作成されたファイル
                    elif any(c in status for c in ['M', 'A', '?', 'R']):
                        abs_path = os.path.join(self.sandbox_dir, rel_path)
                        if os.path.exists(abs_path) and not os.path.isdir(abs_path):
                            try:
                                with open(abs_path, "r", encoding="utf-8") as f:
                                    modified_files[rel_path] = f.read()
                            except Exception:
                                pass
        else:
            # Gitを使用しない場合のフォールバック（本番とサンドボックスの手動比較）
            current_files = self.get_files_state()

            for root, dirs, files in os.walk(self.workspace_dir):
                if ".git" in root or ".venv" in root or "__pycache__" in root:
                    continue
                for file in files:
                    abs_prod = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_prod, self.workspace_dir)
                    abs_sandbox = os.path.join(self.sandbox_dir, rel_path)

                    if not os.path.exists(abs_sandbox):
                        deleted_files.append(rel_path)
                    else:
                        try:
                            with open(abs_prod, "r", encoding="utf-8") as f_p:
                                p_content = f_p.read()
                            with open(abs_sandbox, "r", encoding="utf-8") as f_s:
                                s_content = f_s.read()
                            if p_content != s_content:
                                modified_files[rel_path] = s_content
                        except Exception:
                            pass

            for rel_path in current_files.keys():
                abs_prod = os.path.join(self.workspace_dir, rel_path)
                if not os.path.exists(abs_prod):
                    abs_sandbox = os.path.join(self.sandbox_dir, rel_path)
                    try:
                        with open(abs_sandbox, "r", encoding="utf-8") as f_s:
                            modified_files[rel_path] = f_s.read()
                    except Exception:
                        pass

        return WorkspaceArtifacts(
            modified_files=modified_files,
            deleted_files=deleted_files
        )

    def get_files_state(self) -> Dict[str, Any]:
        """現在のファイルの状態を走査して状態マップを生成します（観測値生成用）。"""
        files_state = {}
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            for root, dirs, files in os.walk(self.sandbox_dir):
                if ".git" in root or ".venv" in root or "__pycache__" in root or ".pytest_cache" in root:
                    continue
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, self.sandbox_dir)
                    if any(x in rel_path.split(os.sep) for x in [".git", ".venv", "__pycache__", ".pytest_cache"]):
                        continue
                    try:
                        files_state[rel_path] = {
                            "size": os.path.getsize(abs_path),
                            "exists": True
                        }
                    except Exception:
                        pass
        return files_state

    def _provision_sandbox(self):
        """本番のワークスペースから一時ディレクトリへ必要なファイルをコピーします。"""
        if self.target_files:
            for rel_path in self.target_files:
                src = os.path.join(self.workspace_dir, rel_path)
                dst = os.path.join(self.sandbox_dir, rel_path)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
        else:
            ignore_patterns = shutil.ignore_patterns(
                ".git", ".venv", "__pycache__", ".pytest_cache", "*.pyc"
            )
            for item in os.listdir(self.workspace_dir):
                if any(x in item for x in ["edd_sandbox_"]):
                    continue
                src = os.path.join(self.workspace_dir, item)
                dst = os.path.join(self.sandbox_dir, item)
                if os.path.isdir(src):
                    if item in [".git", ".venv", "__pycache__", ".pytest_cache"]:
                        continue
                    shutil.copytree(src, dst, ignore=ignore_patterns, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

    def _init_git_repository(self):
        """一時ディレクトリ内で Git リポジトリを初期化し、初期状態をコミットします。"""
        subprocess.run(["git", "init"], cwd=self.sandbox_dir, capture_output=True, text=True)
        self.run_git(["config", "user.name", "EDD Agent"])
        self.run_git(["config", "user.email", "agent@example.com"])
        self.run_git(["add", "."])
        self.run_git(["commit", "-m", "initial state"])
