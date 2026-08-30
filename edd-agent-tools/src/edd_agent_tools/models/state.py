"""
State Management Models for edd-agent-tools
"""

from enum import IntEnum
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class SkillTier(IntEnum):
    """スキルのセキュリティ・権限階層を定義する列挙型"""
    SANDBOX = 0          # 暫定 / 新規スキルのテスト用
    READ_ONLY = 1        # Read-Only: ファイルの読み込みのみ許可
    DRAFT_ONLY = 2       # Draft-Only: 提案ファイルの作成のみ許可
    ACTION_ALLOWED = 3   # Action-Allowed: すべての実アクションを許可


class SkillEntry(BaseModel):
    """スキルまたはエージェントのディレクトリパス"""
    path: Path = Field(..., description="カスタムスキルフォルダへのパス")
    name: Optional[str] = Field(None, description="探索エントリの論理名（別名）")


class InheritEntry(BaseModel):
    """継承元のマニフェスト定義ファイルパス"""
    path: Path = Field(..., description="継承元の共通マニフェストファイルへのパス")


class ProjectSkillInfo(BaseModel):
    """skills_state.json で管理される各スキル/エージェントのプロジェクト品質メタデータ"""
    tier: SkillTier = Field(SkillTier.SANDBOX, description="スキルの権限階層")


class SkillsStateJson(BaseModel):
    """ADK公式仕様に準拠した、3つの基本フィールドを持つ skills_state.json 用の基本スキーマモデル。"""
    entries: List[SkillEntry] = Field(..., description="スキル探索対象のパスリスト")
    inherits: List[InheritEntry] = Field(default_factory=list, description="継承元設定ファイルのリスト")
    exclude: List[str] = Field(default_factory=list, description="除外するスキル名のリスト")

    skills: Dict[str, ProjectSkillInfo] = Field(default_factory=dict, description="登録されている各スキルの品質ステータス情報")
    agents: Dict[str, ProjectSkillInfo] = Field(default_factory=dict, description="登録されている各自律エージェントの品質ステータス情報")
