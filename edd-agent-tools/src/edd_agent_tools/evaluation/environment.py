import os
import shutil
import subprocess
import gymnasium as gym
from gymnasium import spaces
from typing import Any, Dict, Tuple, List
from edd_agent_tools.models import WorkspaceArtifacts

class LocalWorkspaceEnv(gym.Env):
    """
    ファイルシステムおよびpytestの検証を行うワークスペース環境。
    自動コーディングエージェントやリファクタリングスキルが動作する Gymnasium 互換のシミュレーション環境です。
    """
    def __init__(self, workspace_dir: str, target_files: List[str] = None, pip_packages: List[str] = None):
        """
        LocalWorkspaceEnv を初期化します。

        Args:
            workspace_dir: 対象とするワークスペース（サンドボックス）ディレクトリの絶対パス。
            target_files: バックアップおよび復元の対象とするワークスペース内の相対ファイルパスのリスト。
            pip_packages: 仮想環境に事前インストールする基本パッケージのリスト。デフォルトは ["pytest"]。
        """
        super().__init__()
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.target_files = target_files or []
        self.pip_packages = pip_packages if pip_packages is not None else ["pytest"]
        
        # Gymnasium 互換のためのアクション空間と状態空間の定義
        self.action_space = spaces.Dict({
            "action": spaces.Text(max_length=50),
            "path": spaces.Text(max_length=256),
            "content": spaces.Text(max_length=100000)
        })
        
        # 観測は、ファイルの状態、pytestの出力、実行ステータスを格納する辞書
        self.observation_space = spaces.Dict({
            "files": spaces.Dict({}),  # 動的に判定されるファイルマップ
            "pytest_output": spaces.Text(max_length=100000),
            "status": spaces.Text(max_length=50)
        })
        
        # バックアップ用の一時ディレクトリパス
        self.backup_dir = os.path.join(self.workspace_dir, ".sandbox_backup")
        self.step_count = 0
        self.max_steps = 15
        
        # 隔離用仮想環境のパス定義
        self.venv_dir = os.path.join(self.workspace_dir, ".venv")
        self.venv_python = os.path.join(self.venv_dir, "bin", "python3")
        self.venv_pip = os.path.join(self.venv_dir, "bin", "pip")

    def reset(self, seed: int = None, options: Dict[str, Any] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """環境を初期状態にリセットし、バックアップしたファイルをリストアします。"""
        super().reset(seed=seed)
        self.step_count = 0
        
        # 1. 隔離用仮想環境の自動構築とパッケージ解決
        self._setup_virtual_env()
        self._install_dependencies()
        
        # 2. バックアップからワークスペースを初期状態に復元
        if os.path.exists(self.backup_dir):
            for file_rel_path in self.target_files:
                src = os.path.join(self.backup_dir, file_rel_path)
                dst = os.path.join(self.workspace_dir, file_rel_path)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                elif os.path.exists(dst):
                    os.remove(dst)
        else:
            # 初回リセット時に、現在のファイルをバックアップ領域に退避
            os.makedirs(self.backup_dir, exist_ok=True)
            for file_rel_path in self.target_files:
                src = os.path.join(self.workspace_dir, file_rel_path)
                dst = os.path.join(self.backup_dir, file_rel_path)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
   
        obs = self._get_observation()
        info = {"message": "Environment reset complete"}
        return obs, info

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        """
        エージェントのアクションを実行し、環境を1ステップ進めます。
        """
        self.step_count += 1
        
        action_type = action.get("action")
        path = action.get("path")
        content = action.get("content", "")
        
        pytest_output = ""
        action_status = "success"
        reward = 0.0
        terminated = False
        truncated = self.step_count >= self.max_steps
        
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
                # 隔離仮想環境内の pytest を用いて実行
                result = subprocess.run(
                    [self.venv_python, "-m", "pytest"],
                    cwd=self.workspace_dir,
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
        
        # 現在の成果物（差分）の情報を取得
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
        """バックアップ領域をクリーンアップします。"""
        if os.path.exists(self.backup_dir):
            try:
                shutil.rmtree(self.backup_dir)
            except Exception:
                pass

    def export_artifacts(self) -> WorkspaceArtifacts:
        """
        初期状態（reset 時のバックアップ）と比較し、変更されたファイル、
        新しく作成されたファイル、および削除されたファイルを抽出します。

        Returns:
            WorkspaceArtifacts: 変更差分情報を保持する Pydantic モデル
        """
        modified_files = {}
        deleted_files = []

        # 現在のファイルの状態を取得
        current_obs = self._get_observation()
        current_files = current_obs.get("files", {})

        # バックアップ元のファイルを走査し、削除または変更されたファイルを特定
        if os.path.exists(self.backup_dir):
            for root, dirs, files in os.walk(self.backup_dir):
                if "__pycache__" in root or ".pytest_cache" in root or ".venv" in root:
                    continue
                for file in files:
                    abs_backup_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_backup_path, self.backup_dir)
                    
                    abs_current_path = os.path.join(self.workspace_dir, rel_path)
                    
                    if not os.path.exists(abs_current_path):
                        # 現在のワークスペースに存在しないので、削除された
                        deleted_files.append(rel_path)
                    else:
                        # 両方に存在するが、中身が異なるか比較
                        try:
                            with open(abs_backup_path, "r", encoding="utf-8") as f_back:
                                back_content = f_back.read()
                            with open(abs_current_path, "r", encoding="utf-8") as f_curr:
                                curr_content = f_curr.read()
                            
                            if back_content != curr_content:
                                modified_files[rel_path] = curr_content
                        except Exception:
                            pass

        # 現在のファイルを走査し、新しく作成されたファイルを特定
        for rel_path in current_files.keys():
            abs_backup_path = os.path.join(self.backup_dir, rel_path)
            if not os.path.exists(abs_backup_path):
                # バックアップに存在しないので、新規作成
                abs_current_path = os.path.join(self.workspace_dir, rel_path)
                try:
                    with open(abs_current_path, "r", encoding="utf-8") as f_curr:
                        modified_files[rel_path] = f_curr.read()
                except Exception:
                    pass

        return WorkspaceArtifacts(
            modified_files=modified_files,
            deleted_files=deleted_files
        )

    def _setup_virtual_env(self):
        """サンドボックス内に隔離用の仮想環境（venv）を構築します。"""
        if not os.path.exists(self.venv_python):
            os.makedirs(self.workspace_dir, exist_ok=True)
            subprocess.run(
                ["python3", "-m", "venv", self.venv_dir],
                check=True,
                capture_output=True
            )

    def _install_dependencies(self):
        """仮想環境に必要なパッケージ（pytestなど）およびプロジェクトの依存ファイルをインストールします。"""
        cache_dir = os.path.expanduser("~/.cache/pip")
        
        # 1. 基本環境パッケージのインストール
        if self.pip_packages:
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir] + self.pip_packages,
                check=True,
                capture_output=True
            )
            
        # 2. プロジェクト固有の依存関係（requirements.txt 等）の自動検知とインストール
        req_txt = os.path.join(self.workspace_dir, "requirements.txt")
        if os.path.exists(req_txt):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "-r", req_txt],
                check=True,
                capture_output=True
            )
            
        pyproject_toml = os.path.join(self.workspace_dir, "pyproject.toml")
        if os.path.exists(pyproject_toml):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "."],
                cwd=self.workspace_dir,
                check=True,
                capture_output=True
            )
            
        setup_py = os.path.join(self.workspace_dir, "setup.py")
        if os.path.exists(setup_py) and not os.path.exists(pyproject_toml):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "."],
                cwd=self.workspace_dir,
                check=True,
                capture_output=True
            )

    def _resolve_safe_path(self, path: str) -> str:
        """指定されたパスがワークスペースディレクトリの外部に出ていないか検証します。"""
        abs_path = os.path.abspath(os.path.join(self.workspace_dir, path))
        if not abs_path.startswith(self.workspace_dir):
            raise PermissionError(f"Access to path outside workspace is restricted: {path}")
        return abs_path

    def _get_observation(self) -> Dict[str, Any]:
        """現在のファイルの状態をスキャンして観測値を生成します（仮想環境や一時ファイルは除外します）。"""
        files_state = {}
        for root, dirs, files in os.walk(self.workspace_dir):
            # バックアップ、仮想環境、キャッシュ等は走査から除外
            if ".sandbox_backup" in root or ".venv" in root or "__pycache__" in root or ".pytest_cache" in root:
                continue
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, self.workspace_dir)
                # ファイルパスの中に除外ディレクトリ名が含まれる場合も弾く
                if any(x in rel_path.split(os.sep) for x in [".sandbox_backup", ".venv", "__pycache__", ".pytest_cache"]):
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
