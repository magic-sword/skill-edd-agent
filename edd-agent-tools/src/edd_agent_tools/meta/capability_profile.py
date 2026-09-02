"""
Capability Profiles (Environment Packaging & Role-based Tool Bundling)

ホワイトペーパー Section 7 (p.40-41, Table 3) 準拠：
エージェントが一度に全スキルを常時ロードして Context Rot を起こすのを防ぐため、
実行ステート、Tier 権限（Read-Only, Draft-Only, Action-Allowed）、および
業務ロール（Analytics, Compliance, Operations 等）に応じたモジュール化プロファイルを管理。
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field

from edd_agent_tools.state import SkillsState
from edd_agent_tools.models.state import SkillTier


class CapabilityProfile(BaseModel):
    """特定のロールや実行状態に応じたスキル・ツール権限バンドル。"""
    profile_name: str = Field(..., description="プロファイル識別名 (e.g., read_only_safe, action_mastered, analytics)")
    description: str = Field("", description="プロファイルの役割説明")
    min_tier: int = Field(1, description="許可される最低 Tier レベル")
    max_tier: int = Field(3, description="許可される最高 Tier レベル")
    allowed_skills: Optional[List[str]] = Field(None, description="明示的に許可されたスキル名のホワイトリスト（None時は全許可）")
    excluded_skills: List[str] = Field(default_factory=list, description="明示的に除外するスキル名")
    system_guardrails: List[str] = Field(default_factory=list, description="プロファイル適用時の運用ガードレール")


class CapabilityProfileManager:
    """Capability Profiles の作成・解決・適用を管理するマネージャー。"""

    DEFAULT_PROFILES = {
        "read_only_safe": CapabilityProfile(
            profile_name="read_only_safe",
            description="Read-Only 操作のみを許可する安全な参照専用プロファイル",
            min_tier=1,
            max_tier=1,
            system_guardrails=["Must not mutate state or execute write commands."]
        ),
        "draft_review": CapabilityProfile(
            profile_name="draft_review",
            description="Draft-Only の生成・レビュー用プロファイル",
            min_tier=1,
            max_tier=2,
            system_guardrails=["Draft outputs must be reviewed by human before committing."]
        ),
        "action_mastered": CapabilityProfile(
            profile_name="action_mastered",
            description="全操作（Action-Allowed / Tier 3）を許可する完全実行プロファイル",
            min_tier=1,
            max_tier=3,
            system_guardrails=["Audit logging required for irreversible actions."]
        )
    }

    def __init__(self, state: Optional[SkillsState] = None):
        self.state = state or SkillsState()
        self.profiles: Dict[str, CapabilityProfile] = dict(self.DEFAULT_PROFILES)

    def register_profile(self, profile: CapabilityProfile):
        """新しい Capability Profile を登録します。"""
        self.profiles[profile.profile_name] = profile

    def get_profile(self, profile_name: str) -> Optional[CapabilityProfile]:
        """指定された名前のプロファイルを取得します。"""
        return self.profiles.get(profile_name)

    def resolve_active_skills(self, profile_name: str) -> List[Dict[str, Any]]:
        """プロファイルに基づいて、現在マウント可能なスキルのリストを解決します。"""
        profile = self.get_profile(profile_name)
        if not profile:
            raise ValueError(f"Capability Profile '{profile_name}' not found.")

        active_skills = []
        for s in self.state.list_skills():
            t_val = s.tier.value if hasattr(s.tier, "value") else int(s.tier or 0)
            
            # Tier フィルタリング
            if not (profile.min_tier <= t_val <= profile.max_tier):
                continue

            # ホワイトリスト・ブラックリスト
            if profile.allowed_skills is not None and s.name not in profile.allowed_skills:
                continue
            if s.name in profile.excluded_skills:
                continue

            active_skills.append({
                "name": s.name,
                "tier": t_val,
                "description": s.description,
                "path": s.root_dir
            })

        return active_skills
