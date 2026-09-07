"""
Workspace Link Manager (WorkspaceLinkManager)

外部プロジェクト（別Gitリポジトリ）と上流スキルリポジトリ（skill-edd-agent）を
透過的に接続し、現場でのスキル利用およびGit差分の完全分離を実現する管理モジュール。
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class WorkspaceLinkConfig(BaseModel):
    """ローカルプロジェクトに配置される .edd.json のデータモデル"""
    upstream_path: str = Field(..., description="上流リポジトリのルートパス")
    upstream_skills_dir: str = Field(..., description="上流リポジトリ内のスキル格納ディレクトリパス")
    linked_at: str = Field(..., description="リンク設定日時 (ISO 8601)")
    upstream_git_origin: Optional[str] = Field(None, description="上流リポジトリの Git remote URL")


class WorkspaceLinkManager:
    """ローカルプロジェクトにおける上流スキルリポジトリのリンクと Git 連携を管理するクラス"""

    CONFIG_FILENAME = ".edd.json"

    def __init__(self, workspace_root: Optional[Path | str] = None):
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()
        self.config_path = self.workspace_root / self.CONFIG_FILENAME

    def get_link_config(self) -> Optional[WorkspaceLinkConfig]:
        """現在設定されている .edd.json のリンク情報を取得します。未設定の場合は None を返します。"""
        if not self.config_path.exists():
            return None
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return WorkspaceLinkConfig(**data)
        except Exception:
            return None

    def link(self, upstream_path: Path | str) -> Dict[str, Any]:
        """指定された上流リポジトリを現在のプロジェクトにリンクします。

        Args:
            upstream_path: リンク先の上流リポジトリルートパス。

        Returns:
            Dict[str, Any]: リンク結果サマリー（上流パス、スキルディレクトリ、検出スキル数等）。
        """
        up_root = Path(upstream_path).resolve()
        if not up_root.exists():
            raise FileNotFoundError(f"指定された上流リポジトリが見つかりません: {upstream_path}")

        # スキル格納ディレクトリの検出 (src/skills または skills)
        skills_dir = None
        for cand in [up_root / "src" / "skills", up_root / "skills", up_root / ".agents" / "skills"]:
            if cand.exists() and cand.is_dir():
                skills_dir = cand
                break

        if skills_dir is None:
            raise ValueError(
                f"上流リポジトリ '{up_root}' 内にスキルディレクトリ (src/skills または skills) が見つかりません。"
            )

        # 上流の Git Remote URL の取得（オプション）
        git_origin = None
        try:
            res = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=str(up_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0 and res.stdout.strip():
                git_origin = res.stdout.strip()
        except Exception:
            pass

        # 検出可能なスキルのリストアップ
        detected_skills = []
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                detected_skills.append(d.name)

        # 設定ファイルの保存
        now_str = datetime.now(timezone.utc).isoformat()
        cfg = WorkspaceLinkConfig(
            upstream_path=str(up_root),
            upstream_skills_dir=str(skills_dir),
            linked_at=now_str,
            upstream_git_origin=git_origin
        )
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(cfg.model_dump_json(indent=2))

        # .gitignore への追記（存在する場合、または新規作成）
        gitignore_path = self.workspace_root / ".gitignore"
        gitignore_updated = self._ensure_gitignore(gitignore_path)

        return {
            "status": "success",
            "upstream_path": str(up_root),
            "upstream_skills_dir": str(skills_dir),
            "detected_skills": detected_skills,
            "skills_count": len(detected_skills),
            "gitignore_updated": gitignore_updated
        }

    def unlink(self) -> bool:
        """現在のリンク設定 (.edd.json) を解除・削除します。"""
        if self.config_path.exists():
            self.config_path.unlink()
            return True
        return False

    def _ensure_gitignore(self, gitignore_path: Path) -> bool:
        """ローカルプロジェクトの .gitignore に .edd.json が含まれていることを保証します。"""
        entry = self.CONFIG_FILENAME
        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text(encoding="utf-8")
                lines = [line.strip() for line in content.splitlines()]
                if entry not in lines and f"/{entry}" not in lines:
                    with open(gitignore_path, "a", encoding="utf-8") as f:
                        if content and not content.endswith("\n"):
                            f.write("\n")
                        f.write(f"\n# edd workspace link config\n{entry}\n")
                    return True
                return False
            except Exception:
                return False
        else:
            try:
                with open(gitignore_path, "w", encoding="utf-8") as f:
                    f.write(f"# edd workspace link config\n{entry}\n")
                return True
            except Exception:
                return False

    def get_upstream_git_status(self) -> Dict[str, Any]:
        """上流リポジトリの Git 変更差分状況を取得します。"""
        cfg = self.get_link_config()
        if not cfg:
            return {"status": "not_linked", "message": "上流リポジトリがリンクされていません。"}

        up_root = Path(cfg.upstream_path)
        if not (up_root / ".git").exists():
            return {"status": "no_git", "message": "上流リポジトリは Git 管理されていません。"}

        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(up_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            changes = [line for line in res.stdout.splitlines() if line.strip()]
            
            # ブランチ情報の取得
            branch_res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(up_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            current_branch = branch_res.stdout.strip() or "HEAD"

            return {
                "status": "success",
                "upstream_path": str(up_root),
                "current_branch": current_branch,
                "has_changes": len(changes) > 0,
                "changed_files": changes
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_upstream_git_diff(self) -> str:
        """上流リポジトリの Git diff を取得します。"""
        cfg = self.get_link_config()
        if not cfg:
            return "エラー: 上流リポジトリがリンクされていません。"

        up_root = Path(cfg.upstream_path)
        try:
            res = subprocess.run(
                ["git", "diff"],
                cwd=str(up_root),
                capture_output=True,
                text=True,
                timeout=10
            )
            return res.stdout if res.stdout else "差分はありません (Working tree clean)。"
        except Exception as e:
            return f"Git diff の取得中にエラーが発生しました: {e}"

    def push_upstream(
        self,
        branch_name: str,
        message: str,
        create_pr: bool = False
    ) -> Dict[str, Any]:
        """上流リポジトリ側でブランチ作成、コミット、プッシュを実行します。"""
        cfg = self.get_link_config()
        if not cfg:
            return {"status": "error", "message": "上流リポジトリがリンクされていません。"}

        up_root = Path(cfg.upstream_path)
        try:
            # 1. ブランチの作成または切り替え
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=str(up_root), check=True, capture_output=True)
            # 2. ステージング
            subprocess.run(["git", "add", "-A"], cwd=str(up_root), check=True, capture_output=True)
            # 3. コミット
            subprocess.run(["git", "commit", "-m", message], cwd=str(up_root), check=True, capture_output=True)
            # 4. プッシュ
            push_res = subprocess.run(["git", "push", "origin", branch_name], cwd=str(up_root), capture_output=True, text=True)
            
            pr_url = None
            if create_pr:
                # gh CLI があれば PR を作成
                pr_res = subprocess.run(
                    ["gh", "pr", "create", "--title", message, "--body", f"Automated skill improvement from downstream workspace.\n\nBranch: `{branch_name}`"],
                    cwd=str(up_root),
                    capture_output=True,
                    text=True
                )
                if pr_res.returncode == 0:
                    pr_url = pr_res.stdout.strip()

            return {
                "status": "success",
                "branch": branch_name,
                "upstream_path": str(up_root),
                "push_output": push_res.stdout,
                "pr_url": pr_url
            }
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
            return {"status": "error", "message": f"Git 操作に失敗しました: {err_msg}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
