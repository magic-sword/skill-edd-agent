from pathlib import Path
from enum import IntEnum
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

class InheritEntry(BaseModel):
    """継承元のマニフェスト定義ファイルパス"""
    path: Path = Field(..., description="継承元の共通マニフェストファイルへのパス")

class ProjectSkillInfo(BaseModel):
    """skills_state.json で管理される各スキル/エージェントのプロジェクト品質メタデータ"""
    tier: SkillTier = Field(SkillTier.SANDBOX, description="スキルの権限階層")

class SkillsStateJson(BaseModel):
    """ADK公式仕様に準拠した、3つの基本フィールドを持つ skills_state.json 用の基本スキーマモデル。

    探索と優先順位のマージ規則:
      1. entries (探索パスの優先順):
         ローカルの entries が最優先され、その後 inherits で指定された継承先の探索パスが順に末尾へ追記されます。
         同名のスキルが複数発見された場合は、探索リストの先頭（ローカル優先）のものがマウントされ、後続はシャドウイング（無視）されます。
      2. inherits (継承元マニフェスト):
         別のマニフェストファイルをインポートし、探索パスを多重解決します。
      3. exclude (除外リストの累積):
         ローカルの除外リストと、すべての継承元で定義された除外リストが累積（論理和マージ）されます。
    """
    entries: list[SkillEntry] = Field(..., description="スキル探索対象のパスリスト")
    inherits: list[InheritEntry] = Field(default_factory=list, description="継承元設定ファイルのリスト")
    exclude: list[str] = Field(default_factory=list, description="除外するスキル名のリスト")

    # プロジェクト独自の拡張メタデータ (論理スキル名をキーにしたオブジェクトマップ形式)
    skills: dict[str, ProjectSkillInfo] = Field(default_factory=dict, description="登録されている各スキルの品質・テストステータス情報")
    agents: dict[str, ProjectSkillInfo] = Field(default_factory=dict, description="登録されている各エージェント/ワークフローの品質・テストステータス情報")
