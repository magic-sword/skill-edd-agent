import os
import sys
import subprocess
from typing import Dict, List, Any, Tuple
from edd_agent_tools.evaluation.models import (
    WorkspaceArtifacts, 
    WorkspaceAction, 
    WorkspaceObservation, 
    FileState, 
    WriteFileAction, 
    ViewFileAction, 
    RunPytestAction
)

class RealWorkspaceEnv:
    """本番環境のプロジェクトフォルダを直接操作する、実ファイルシステム環境。

    一時サンドボックスによる隔離を行わず、引数で渡された `workspace_dir` への
    直接の読み書き、および pytest コマンドの直接実行を行います。
    """
    def __init__(self, workspace_dir: str, max_steps: int = 15):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.step_count = 0
        self.max_steps = max_steps
        
        # 本番プロジェクト直下の .venv を優先利用
        host_venv = os.path.join(self.workspace_dir, ".venv")
        if os.path.exists(host_venv):
            self.venv_python = os.path.join(host_venv, "bin", "python3")
        else:
            self.venv_python = sys.executable

    def reset(self, seed: int = None, options: Dict[str, Any] = None) -> Tuple[WorkspaceObservation, Dict[str, Any]]:
        """環境をリセット（カウンタクリアおよびファイルスキャン）します。"""
        self.step_count = 0
        obs = self._get_observation()
        info = {"message": "Real environment reset complete (no isolation)"}
        return obs, info

    def step(self, action: WorkspaceAction) -> Tuple[WorkspaceObservation, float, bool, bool, Dict[str, Any]]:
        """本番環境に対して直接アクションを実行し、1ステップ進めます。"""
        self.step_count += 1
        
        if not isinstance(action, (WriteFileAction, ViewFileAction, RunPytestAction)):
            raise TypeError("action must be a WorkspaceAction (WriteFileAction, ViewFileAction, or RunPytestAction)")

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
                safe_path = self._resolve_path(path)
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                with open(safe_path, "w", encoding="utf-8") as f:
                    f.write(content)
                action_status = "file_written"
                
            elif action_type == "view_file" and path:
                safe_path = self._resolve_path(path)
                if os.path.exists(safe_path):
                    with open(safe_path, "r", encoding="utf-8") as f:
                        pytest_output = f.read()
                    action_status = "file_viewed"
                else:
                    action_status = f"error: file not found at {path}"
                    
            elif action_type == "run_pytest":
                # 本番のワークスペースを作業ディレクトリとして pytest を直接実行
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
            obs.pytest_output = pytest_output
        obs.status = action_status
        
        info = {
            "step": self.step_count,
            "action_executed": action_type,
            "note": "Executed directly on production directory (non-isolated)"
        }
        
        return obs, reward, terminated, truncated, info

    def close(self) -> None:
        """環境を終了します（本番環境なのでファイルの消去は行いません）。"""
        pass

    def export_artifacts(self) -> WorkspaceArtifacts:
        """本番環境を直接書き換えるため、差分（成果物）は空として返却します。"""
        return WorkspaceArtifacts(modified_files={}, deleted_files=[])

    def _resolve_path(self, relative_path: str) -> str:
        """プロジェクト外への書き込み防止ガード。"""
        resolved = os.path.abspath(os.path.join(self.workspace_dir, relative_path))
        if not resolved.startswith(self.workspace_dir):
            raise PermissionError(f"Access denied: path '{relative_path}' is outside workspace '{self.workspace_dir}'")
        return resolved

    def _get_observation(self) -> WorkspaceObservation:
        """現在のファイルの状態をスキャンして観測値を生成します。"""
        files_state = {}
        # 本番フォルダ配下のファイルを再帰的にスキャン
        for root, dirs, files in os.walk(self.workspace_dir):
            # .git や .venv などの管理用ディレクトリはスキップ
            if any(p in root for p in [".git", ".venv", "__pycache__", ".sandbox_temp"]):
                continue
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_dir)
                try:
                    size = os.path.getsize(full_path)
                    files_state[rel_path] = FileState(size=size, exists=True)
                except Exception:
                    pass
        return WorkspaceObservation(
            files=files_state,
            pytest_output="",
            status="idle"
        )
