import os
import shutil
import tempfile
import subprocess
import gymnasium as gym
from gymnasium import spaces
from typing import Any, Dict, Tuple, List
from edd_agent_tools.models import WorkspaceArtifacts

class LocalWorkspaceEnv(gym.Env):
    """
    一時的なOSディレクトリ（サンドボックス）でファイルシステム操作およびpytestの検証を行う環境。
    Gitを用いて変更のロールバックと差分抽出を高速・正確に処理します。
    """
    def __init__(
        self, 
        workspace_dir: str, 
        target_files: List[str] = None, 
        pip_packages: List[str] = None,
        use_git: bool = True,
        use_host_venv: bool = True
    ):
        """
        LocalWorkspaceEnv を初期化します。

        Args:
            workspace_dir: 対象とする本番ワークスペース（親プロジェクト）の絶対パス。
            target_files: サンドボックスに初期配置する対象ファイルの相対パスリスト。指定しない場合は全体を同期します。
            pip_packages: 隔離仮想環境（use_host_venv=False時）にインストールするパッケージ。
            use_git: Git を使ったチェックポイント管理および差分検出を行うか。
            use_host_venv: ホストの .venv（または実行中のPython環境）を再利用するか。
        """
        super().__init__()
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.target_files = target_files or []
        self.pip_packages = pip_packages if pip_packages is not None else ["pytest"]
        self.use_git = use_git
        self.use_host_venv = use_host_venv
        
        # Gymnasium 互換のためのアクション空間と状態空間の定義
        self.action_space = spaces.Dict({
            "action": spaces.Text(max_length=50),
            "path": spaces.Text(max_length=256),
            "content": spaces.Text(max_length=100000)
        })
        
        self.observation_space = spaces.Dict({
            "files": spaces.Dict({}),
            "pytest_output": spaces.Text(max_length=100000),
            "status": spaces.Text(max_length=50)
        })
        
        self.step_count = 0
        self.max_steps = 15
        
        # サンドボックス用の一時フォルダ（reset()で動的に作成されます）
        self.sandbox_dir = None
        self.venv_dir = None
        self.venv_python = None
        self.venv_pip = None

    def reset(self, seed: int = None, options: Dict[str, Any] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """環境をリセットし、OSの一時領域に新しいサンドボックスを構築します。"""
        super().reset(seed=seed)
        self.step_count = 0
        
        # 1. 古いサンドボックスのクリーンアップ
        self.close()
        
        # 2. 新しい一時フォルダを OS の一時領域に作成
        self.sandbox_dir = tempfile.mkdtemp(prefix="edd_sandbox_")
        
        # 3. 本番ディレクトリから一時フォルダへファイルをプロビジョニング
        self._provision_sandbox()
        
        # 4. Git チェックポイントの設定
        if self.use_git:
            self._init_git_repository()
            
        # 5. 仮想環境インタプリタの特定/構築
        if self.use_host_venv:
            # 親プロジェクト直下の .venv 内の Python を優先して使用
            host_venv = os.path.join(self.workspace_dir, ".venv")
            if os.path.exists(host_venv):
                self.venv_python = os.path.join(host_venv, "bin", "python3")
                self.venv_pip = os.path.join(host_venv, "bin", "pip")
            else:
                import sys
                self.venv_python = sys.executable
                self.venv_pip = None
        else:
            # 隔離用仮想環境の作成
            self.venv_dir = os.path.join(self.sandbox_dir, ".venv")
            self.venv_python = os.path.join(self.venv_dir, "bin", "python3")
            self.venv_pip = os.path.join(self.venv_dir, "bin", "pip")
            self._setup_virtual_env()
            self._install_dependencies()
            
        obs = self._get_observation()
        info = {"message": "Environment reset complete in sandbox"}
        return obs, info

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        """エージェントのアクションを実行し、一時サンドボックスを進めます。"""
        self.step_count += 1
        
        action_type = action.get("action")
        path = action.get("path")
        content = action.get("content", "")
        
        pytest_output = ""
        action_status = "success"
        reward = 0.0
        terminated = False
        truncated = self.step_count >= self.max_steps
        
        if not self.sandbox_dir:
            return self._get_observation(), -1.0, False, True, {"error": "Sandbox not initialized"}
            
        try:
            if action_type == "write_file" and path:
                safe_path = self._resolve_safe_path(path)
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                with open(safe_path, "w", encoding="utf-8") as f:
                    f.write(content)
                action_status = "file_written"
                
            elif action_type == "view_file" and path:
                safe_path = self._resolve_safe_path(path)
                if os.path.exists(safe_path):
                    with open(safe_path, "r", encoding="utf-8") as f:
                        pytest_output = f.read()
                    action_status = "file_viewed"
                else:
                    action_status = f"error: file not found at {path}"
                    
            elif action_type == "run_pytest":
                # pytest を一時サンドボックスを作業ディレクトリとして実行
                result = subprocess.run(
                    [self.venv_python, "-m", "pytest"],
                    cwd=self.sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                pytest_output = result.stdout + "\n" + result.stderr
                if result.returncode == 0:
                    reward = 1.0
                    terminated = True
                    action_status = "pytest_passed"
                else:
                    reward = 0.0
                    action_status = "pytest_failed"
            else:
                action_status = f"error: unknown action {action_type}"
        except Exception as e:
            action_status = f"error: {str(e)}"
            reward = -0.1
            
        obs = self._get_observation()
        if pytest_output:
            obs["pytest_output"] = pytest_output
        obs["status"] = action_status
        
        # 成果物（差分）情報をエクスポート
        artifacts = self.export_artifacts()
        info = {
            "step": self.step_count,
            "action_executed": action_type,
            "artifacts_summary": {
                "modified_count": len(artifacts.modified_files),
                "deleted_count": len(artifacts.deleted_files),
                "modified_files": list(artifacts.modified_files.keys()),
                "deleted_files": artifacts.deleted_files
            }
        }
        
        return obs, reward, terminated, truncated, info

    def close(self):
        """一時的に作成したサンドボックスディレクトリを物理消去します。"""
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            try:
                shutil.rmtree(self.sandbox_dir)
            except Exception:
                pass
        self.sandbox_dir = None

    def export_artifacts(self) -> WorkspaceArtifacts:
        """
        初期状態（reset()時）と比較し、変更されたファイル、
        新しく作成されたファイル、および削除されたファイルを抽出します。
        """
        modified_files = {}
        deleted_files = []

        if not self.sandbox_dir:
            return WorkspaceArtifacts()

        if self.use_git:
            # 1. git status --porcelain -z を用いて、変更されたファイルを特定
            result = self._run_git_command(["status", "--porcelain", "-z"])
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
            current_obs = self._get_observation()
            current_files = current_obs.get("files", {})

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
                # サンドボックスフォルダ自身や一時的なバックアップはコピー対象外にする
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

    def _run_git_command(self, args: list[str]) -> subprocess.CompletedProcess:
        """混同を防ぐために --git-dir と --work-tree を強制して Git コマンドを実行します。"""
        if not self.sandbox_dir:
            raise RuntimeError("Sandbox directory is not initialized.")
            
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

    def _init_git_repository(self):
        """一時ディレクトリ内で Git リポジトリを初期化し、初期状態をコミットします。"""
        # git init
        subprocess.run(["git", "init"], cwd=self.sandbox_dir, capture_output=True, text=True)
        # ユーザー未設定時に備えてダミー設定
        self._run_git_command(["config", "user.name", "EDD Agent"])
        self._run_git_command(["config", "user.email", "agent@example.com"])
        # 初期状態のコミット
        self._run_git_command(["add", "."])
        self._run_git_command(["commit", "-m", "initial state"])

    def _setup_virtual_env(self):
        """サンドボックス内に隔離用の仮想環境（venv）を構築します。"""
        if not os.path.exists(self.venv_python):
            os.makedirs(self.sandbox_dir, exist_ok=True)
            subprocess.run(
                ["python3", "-m", "venv", self.venv_dir],
                check=True,
                capture_output=True
            )

    def _install_dependencies(self):
        """仮想環境に必要なパッケージ（pytestなど）およびプロジェクトの依存ファイルをインストールします。"""
        cache_dir = os.path.expanduser("~/.cache/pip")
        
        if self.pip_packages:
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir] + self.pip_packages,
                check=True,
                capture_output=True
            )
            
        req_txt = os.path.join(self.sandbox_dir, "requirements.txt")
        if os.path.exists(req_txt):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "-r", req_txt],
                check=True,
                capture_output=True
            )
            
        pyproject_toml = os.path.join(self.sandbox_dir, "pyproject.toml")
        if os.path.exists(pyproject_toml):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "."],
                cwd=self.sandbox_dir,
                check=True,
                capture_output=True
            )
            
        setup_py = os.path.join(self.sandbox_dir, "setup.py")
        if os.path.exists(setup_py) and not os.path.exists(pyproject_toml):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "."],
                cwd=self.sandbox_dir,
                check=True,
                capture_output=True
            )

    def _resolve_safe_path(self, path: str) -> str:
        """指定されたパスが一時ディレクトリの外部に出ていないか検証します。"""
        if not self.sandbox_dir:
            raise RuntimeError("Sandbox directory is not initialized.")
        abs_path = os.path.abspath(os.path.join(self.sandbox_dir, path))
        if not abs_path.startswith(self.sandbox_dir):
            raise PermissionError(f"Access to path outside sandbox is restricted: {path}")
        return abs_path

    def _get_observation(self) -> Dict[str, Any]:
        """現在のファイルの状態をスキャンして観測値を生成します。"""
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
        return {
            "files": files_state,
            "pytest_output": "",
            "status": "idle"
        }
