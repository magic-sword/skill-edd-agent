import os
import shutil
from abc import ABC, abstractmethod
from typing import Dict, Any

from edd_agent_tools.models import WorkspaceArtifacts


class ArtifactApplier(ABC):
    """エージェントが生成した成果物（アーティファクト）の適用を抽象化する抽象基底クラス。"""
    
    @abstractmethod
    def apply(self, artifacts: WorkspaceArtifacts) -> None:
        """成果物（差分データ）を適用します。"""
        pass


class LocalFileApplier(ArtifactApplier):
    """ローカルのファイルシステムに対して直接成果物を適用するアプライヤー。"""
    
    def __init__(
        self, 
        target_dir: str, 
        dry_run: bool = False, 
        backup: bool = True,
        backup_dir: str = None
    ):
        """
        LocalFileApplier を初期化します。

        Args:
            target_dir: 適用先となる本番ディレクトリの絶対パス。
            dry_run: Trueの場合、実際のファイル操作は行わず、適用予定のログ出力のみを行います。
            backup: Trueの場合、変更・削除される元のファイルを事前にバックアップ領域に退避します。
            backup_dir: バックアップファイルを保存するディレクトリ。指定しない場合は target_dir/.apply_backup になります。
        """
        self.target_dir = os.path.abspath(target_dir)
        self.dry_run = dry_run
        self.backup = backup
        self.backup_dir = backup_dir or os.path.join(self.target_dir, ".apply_backup")

    def apply(self, artifacts: WorkspaceArtifacts) -> None:
        """成果物（差分データ）を指定された本番ディレクトリに適用します。"""
        if self.dry_run:
            print(f"[LocalFileApplier] [DRY-RUN] Starting dry-run application to {self.target_dir}")
        else:
            print(f"[LocalFileApplier] Starting application to {self.target_dir}")
            os.makedirs(self.target_dir, exist_ok=True)
            if self.backup:
                os.makedirs(self.backup_dir, exist_ok=True)

        # 1. バックアップの作成 (適用する前に元の状態を保存)
        if self.backup and not self.dry_run:
            # 変更・新規作成されるファイルのバックアップ
            for rel_path in artifacts.modified_files.keys():
                src_path = os.path.join(self.target_dir, rel_path)
                if os.path.exists(src_path):
                    dst_path = os.path.join(self.backup_dir, rel_path)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    print(f"[LocalFileApplier] Backed up original file: {rel_path}")

            # 削除されるファイルのバックアップ
            for rel_path in artifacts.deleted_files:
                src_path = os.path.join(self.target_dir, rel_path)
                if os.path.exists(src_path):
                    dst_path = os.path.join(self.backup_dir, rel_path)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                    print(f"[LocalFileApplier] Backed up original file (to be deleted): {rel_path}")

        # 2. 変更・新規作成ファイルの適用
        for rel_path, content in artifacts.modified_files.items():
            dst_path = os.path.join(self.target_dir, rel_path)
            if self.dry_run:
                print(f"[LocalFileApplier] [DRY-RUN] Will create/modify file: {rel_path}")
            else:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                with open(dst_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[LocalFileApplier] Applied modified/new file: {rel_path}")

        # 3. 削除ファイルの適用
        for rel_path in artifacts.deleted_files:
            dst_path = os.path.join(self.target_dir, rel_path)
            if os.path.exists(dst_path):
                if self.dry_run:
                    print(f"[LocalFileApplier] [DRY-RUN] Will delete file: {rel_path}")
                else:
                    os.remove(dst_path)
                    print(f"[LocalFileApplier] Deleted file: {rel_path}")

        print(f"[LocalFileApplier] Application completed successfully.")
