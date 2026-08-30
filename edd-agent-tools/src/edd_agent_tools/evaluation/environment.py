import os
import subprocess
import gymnasium as gym
from gymnasium import spaces
from typing import Any, Dict, Tuple, List, Union
from pydantic import TypeAdapter
from edd_agent_tools.evaluation.sandbox import GitSandbox
from .models import WorkspaceArtifacts, WorkspaceAction, WorkspaceObservation, FileState, WriteFileAction, ViewFileAction, RunPytestAction

class LocalWorkspaceEnv(gym.Env):
    """
    一時的なOSディレクトリ（サンドボックス）でファイルシステム操作およびpytestの検証を行う環境。
    低レイヤーのファイル操作とGitステート制御は内部の GitSandbox クラスに委譲します。
    """
    def __init__(
        self, 
        workspace_dir: str = ".", 
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
        self.pip_packages = pip_packages if pip_packages is not None else ["pytest"]
        self.use_host_venv = use_host_venv
        
        # GitSandbox の初期化
        self.sandbox = GitSandbox(workspace_dir, target_files, use_git)
        
        # Gymnasium 互換のためのアクション空間と状態空間の定義
        # (内部的には Pydantic オブジェクトを使用しますが、Gymnasiumのインターフェース規定に従い定義は残します)
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
        
        # 仮想環境インタプリタのパス
        self.venv_dir = None
        self.venv_python = None
        self.venv_pip = None
        
        # アクションの検証用 TypeAdapter
        self._action_adapter = TypeAdapter(WorkspaceAction)

    @property
    def sandbox_dir(self) -> str | None:
        """サンドボックスディレクトリの絶対パスプロパティ。"""
        return self.sandbox.sandbox_dir

    def reset(self, seed: int = None, options: Dict[str, Any] = None) -> Tuple[WorkspaceObservation, Dict[str, Any]]:
        """環境をリセットし、新しいサンドボックス（一時フォルダ）を構築します。"""
        super().reset(seed=seed)
        self.step_count = 0
        
        # 1. 新しいサンドボックスを作成（古いものは自動消去）
        self.sandbox.create()
        
        # 2. 仮想環境インタプリタの特定/構築
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
            self.venv_dir = os.path.join(self.sandbox.sandbox_dir, ".venv")
            self.venv_python = os.path.join(self.venv_dir, "bin", "python3")
            self.venv_pip = os.path.join(self.venv_dir, "bin", "pip")
            self._setup_virtual_env()
            self._install_dependencies()
            
        obs = self._get_observation()
        info = {"message": "Environment reset complete in sandbox"}
        return obs, info

    def step(self, action: WorkspaceAction) -> Tuple[WorkspaceObservation, float, bool, bool, Dict[str, Any]]:
        """エージェントのアクションを実行し、環境を1ステップ進めます。"""
        self.step_count += 1
        
        if not isinstance(action, (WriteFileAction, ViewFileAction, RunPytestAction)):
            raise TypeError("action must be a WorkspaceAction (WriteFileAction, ViewFileAction, or RunPytestAction)")
            
        if not self.sandbox.sandbox_dir:
            obs = self._get_observation()
            obs.status = "error: Sandbox not initialized"
            return obs, -1.0, False, True, {"error": "Sandbox not initialized"}

        action_dict = action.model_dump()
        action_type = action_dict.get("action")
        path = action_dict.get("path")
        content = action_dict.get("content", "")
        
        pytest_output = ""
        action_status = "success"
        reward = 0.0
        terminated = False
        truncated = self.step_count >= self.max_steps
        
        try:
            if action_type == "write_file" and path:
                safe_path = self.sandbox.resolve_path(path)
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                with open(safe_path, "w", encoding="utf-8") as f:
                    f.write(content)
                action_status = "file_written"
                
            elif action_type == "view_file" and path:
                safe_path = self.sandbox.resolve_path(path)
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
                    cwd=self.sandbox.sandbox_dir,
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
            obs.pytest_output = pytest_output
        obs.status = action_status
        
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
        """一時的に作成したサンドボックスを物理消去します。"""
        self.sandbox.cleanup()

    def export_artifacts(self) -> WorkspaceArtifacts:
        """初期状態と比較し、変更・新規作成・削除されたファイルを抽出します。"""
        return self.sandbox.get_artifacts()

    def _setup_virtual_env(self):
        """サンドボックス内に隔離用の仮想環境（venv）を構築します。"""
        if not os.path.exists(self.venv_python):
            os.makedirs(self.sandbox.sandbox_dir, exist_ok=True)
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
            
        req_txt = os.path.join(self.sandbox.sandbox_dir, "requirements.txt")
        if os.path.exists(req_txt):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "-r", req_txt],
                check=True,
                capture_output=True
            )
            
        pyproject_toml = os.path.join(self.sandbox.sandbox_dir, "pyproject.toml")
        if os.path.exists(pyproject_toml):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "."],
                cwd=self.sandbox.sandbox_dir,
                check=True,
                capture_output=True
            )
            
        setup_py = os.path.join(self.sandbox.sandbox_dir, "setup.py")
        if os.path.exists(setup_py) and not os.path.exists(pyproject_toml):
            subprocess.run(
                [self.venv_pip, "install", "--cache-dir", cache_dir, "."],
                cwd=self.sandbox.sandbox_dir,
                check=True,
                capture_output=True
            )

    def _get_observation(self) -> WorkspaceObservation:
        """現在のファイルの状態をスキャンして観測値を生成します。"""
        files_state = {}
        for path, info in self.sandbox.get_files_state().items():
            files_state[path] = FileState(
                size=info.get("size", 0),
                exists=info.get("exists", True)
            )
        return WorkspaceObservation(
            files=files_state,
            pytest_output="",
            status="idle"
        )
