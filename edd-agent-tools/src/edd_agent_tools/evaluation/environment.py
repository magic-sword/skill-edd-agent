"""
Local Workspace Environment for edd-agent-tools

一時的なOSディレクトリ（サンドボックス）でファイルシステム操作およびpytestの検証を行う環境。
"""

import os
import shutil
import tempfile
import subprocess
from typing import Any, Dict, Tuple, List, Union, Optional, Literal
from pydantic import BaseModel, Field, TypeAdapter
from edd_agent_tools.core.protocols import WorkspaceEnvProtocol


class WorkspaceArtifacts(BaseModel):
    """ワークスペース環境からエクスポートされる成果物のスキーマ定義。"""
    modified_files: Dict[str, str] = Field(
        default_factory=dict,
        description="新規作成または修正されたファイルの相対パスとコンテンツのマップ"
    )
    deleted_files: List[str] = Field(
        default_factory=list,
        description="削除されたファイルの相対パスのリスト"
    )


class WriteFileAction(BaseModel):
    """指定された相対パスのファイルにコンテンツを書き込むアクション定義。"""
    action: Literal["write_file"] = "write_file"
    path: str
    content: str = ""


class ViewFileAction(BaseModel):
    """指定された相対パスのファイル内容を閲覧するアクション定義。"""
    action: Literal["view_file"] = "view_file"
    path: str


class RunPytestAction(BaseModel):
    """pytestを実行するアクション定義。"""
    action: Literal["run_pytest"] = "run_pytest"


WorkspaceAction = Union[WriteFileAction, ViewFileAction, RunPytestAction]


class FileState(BaseModel):
    """個別ファイルの状態情報。"""
    size: int = 0
    exists: bool = True


class WorkspaceObservation(BaseModel):
    """ワークスペース観測空間のモデル。"""
    files: Dict[str, FileState] = Field(default_factory=dict)
    pytest_output: str = ""
    status: str = "idle"


class GitSandbox:
    """一時ディレクトリ（サンドボックス）でファイル操作およびGitステート制御を行うクラス。"""
    def __init__(self, workspace_dir: str, target_files: Optional[List[str]] = None, use_git: bool = True):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.target_files = target_files or []
        self.use_git = use_git
        self.sandbox_dir: Optional[str] = None

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
            raise ValueError(f"Path traversal detected: {path}")
        return abs_path

    def _provision_sandbox(self):
        """本番ディレクトリから対象ファイルを一時ディレクトリへ安全にコピーします。"""
        if not self.sandbox_dir:
            return

        if not self.target_files:
            # target_filesが指定されていない場合はワークスペース全体をコピー（巨大な外部資料・キャッシュは除外）
            ignored_top_items = {
                ".git", ".venv", "__pycache__", "dist", "build", ".pytest_cache",
                "awesome-claude-skills-master", "Agent Skills_Day_3.pdf"
            }
            for item in os.listdir(self.workspace_dir):
                if item in ignored_top_items or item.endswith(".pdf"):
                    continue
                s = os.path.join(self.workspace_dir, item)
                d = os.path.join(self.sandbox_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, symlinks=True, ignore=shutil.ignore_patterns("*.pyc", "__pycache__", ".git"))
                else:
                    shutil.copy2(s, d)
        else:
            # 指定された target_files のみ同期
            for rel_path in self.target_files:
                src_path = os.path.join(self.workspace_dir, rel_path)
                dst_path = os.path.join(self.sandbox_dir, rel_path)
                if os.path.exists(src_path):
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path, symlinks=True)
                    else:
                        shutil.copy2(src_path, dst_path)

    def _init_git_repository(self):
        """サンドボックスを隔離された Git リポジトリとして初期化し、初期コミットを作成します。"""
        try:
            self.run_git(["init"])
            self.run_git(["config", "user.name", "EDD Agent Sandbox"])
            self.run_git(["config", "user.email", "sandbox@edd-agent.local"])
            self.run_git(["add", "-A"])
            self.run_git(["commit", "-m", "Initial sandbox snapshot", "--allow-empty"])
        except Exception:
            pass

    def get_artifacts(self) -> WorkspaceArtifacts:
        """Gitのステータスまたはファイル比較により差分ファイルを抽出します。"""
        if not self.sandbox_dir:
            return WorkspaceArtifacts()

        modified_files: Dict[str, str] = {}
        deleted_files: List[str] = []

        if self.use_git and os.path.exists(os.path.join(self.sandbox_dir, ".git")):
            res = self.run_git(["status", "--porcelain"])
            for line in res.stdout.splitlines():
                if not line.strip():
                    continue
                status_code = line[:2]
                file_path = line[3:].strip()
                abs_path = os.path.join(self.sandbox_dir, file_path)
                if "D" in status_code:
                    deleted_files.append(file_path)
                else:
                    if os.path.exists(abs_path) and os.path.isfile(abs_path):
                        try:
                            with open(abs_path, "r", encoding="utf-8") as f:
                                modified_files[file_path] = f.read()
                        except Exception:
                            pass
        return WorkspaceArtifacts(modified_files=modified_files, deleted_files=deleted_files)

    def get_files_state(self) -> Dict[str, Dict[str, Any]]:
        """サンドボックス内のファイル状態辞書を生成します。"""
        if not self.sandbox_dir:
            return {}
        state = {}
        for root, _, files in os.walk(self.sandbox_dir):
            if ".git" in root or "__pycache__" in root or ".venv" in root:
                continue
            for f in files:
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, self.sandbox_dir)
                try:
                    state[rel_path] = {"size": os.path.getsize(abs_path), "exists": True}
                except Exception:
                    pass
        return state


class LocalWorkspaceEnv:
    """
    一時的なOSディレクトリ（サンドボックス）でファイルシステム操作およびpytestの検証を行う環境。
    低レイヤーのファイル操作とGitステート制御は内部の GitSandbox クラスに委譲します。
    """
    def __init__(
        self, 
        workspace_dir: str = ".", 
        target_files: Optional[List[str]] = None, 
        pip_packages: Optional[List[str]] = None,
        use_git: bool = True,
        use_host_venv: bool = True
    ):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.pip_packages = pip_packages if pip_packages is not None else ["pytest"]
        self.use_host_venv = use_host_venv
        
        # GitSandbox の初期化
        self.sandbox = GitSandbox(workspace_dir, target_files, use_git)
        self.step_count = 0
        self.max_steps = 15
        
        self.venv_dir = None
        self.venv_python = None
        self.venv_pip = None
        self._action_adapter = TypeAdapter(WorkspaceAction)

    @property
    def sandbox_dir(self) -> Optional[str]:
        """サンドボックスディレクトリの絶対パスプロパティ。"""
        return self.sandbox.sandbox_dir

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[WorkspaceObservation, Dict[str, Any]]:
        """環境をリセットし、新しいサンドボックス（一時フォルダ）を構築します。"""
        self.step_count = 0
        self.sandbox.create()
        
        if self.use_host_venv:
            host_venv = os.path.join(self.workspace_dir, ".venv")
            if os.path.exists(host_venv):
                self.venv_python = os.path.join(host_venv, "bin", "python3")
                self.venv_pip = os.path.join(host_venv, "bin", "pip")
            else:
                import sys
                self.venv_python = sys.executable
                self.venv_pip = None
        else:
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
