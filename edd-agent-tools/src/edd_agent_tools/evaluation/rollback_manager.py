"""
Skill Rollback Manager (SkillRollbackManager)

Google 『Agent Skills』ホワイトペーパー（May 2026）Table 1 Pattern 5 (p.20), Figure 10 (p.37) 準拠：
本番運用中または評価フェーズにおいて Context Rot、性能低下、または回帰（Regression）が検知された際、
スキルの権限階層（Tier）を安全な前段階へ即時降格し、A2A Agent Card を自動再同期し、
ロールバック履歴（監査証跡）を発行する自動復旧マネージャー。
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from edd_agent_tools.state import SkillsState
from edd_agent_tools.models import SkillTier
from edd_agent_tools.packaging.card_sync import AgentCardSynchronizer


class RollbackReceipt(BaseModel):
    """ロールバック実行受領書"""
    receipt_id: str
    skill_name: str
    previous_tier: int
    new_tier: int
    timestamp: str
    reason: str
    agent_card_synced: bool
    status: str = "SUCCESS"


class SkillRollbackManager:
    """スキルの権限降格および安全なロールバックを統括するマネージャー"""

    def __init__(
        self,
        state: Optional[SkillsState] = None,
        workspace_root: Optional[Path] = None,
        history_file: Optional[Path] = None
    ):
        self.workspace_root = workspace_root or Path.cwd()
        self.state = state or SkillsState(project_root=self.workspace_root)
        self.card_sync = AgentCardSynchronizer(state=self.state)
        self.history_file = history_file or (self.workspace_root / ".agents" / "rollback_history.json")

    def rollback_skill(
        self,
        skill_name: str,
        target_tier: int = 1,
        reason: str = "Automated rollback due to detected anomalies"
    ) -> RollbackReceipt:
        """指定されたスキルを指定 Tier へ降格し、Agent Card を再同期します。

        Args:
            skill_name: ロールバック対象のスキル名。
            target_tier: 降格先の目標 Tier (デフォルト 1: READ_ONLY)。
            reason: ロールバック理由。

        Returns:
            RollbackReceipt: ロールバック結果受領書。
        """
        current_tier = self.state.get_skill_tier(skill_name)
        if current_tier < target_tier:
            raise ValueError(
                f"Cannot rollback skill '{skill_name}': target tier ({target_tier}) is higher than current ({current_tier})."
            )

        # 1. SkillsState の更新
        self.state.set_skill_tier(skill_name, target_tier)

        # 2. Agent Card の自動再同期
        synced = False
        try:
            self.card_sync.sync_to_file()
            synced = True
        except Exception:
            pass

        # 3. 受領書の発行と記録
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        import uuid
        receipt = RollbackReceipt(
            receipt_id=f"rb_{uuid.uuid4().hex[:8]}",
            skill_name=skill_name,
            previous_tier=current_tier,
            new_tier=target_tier,
            timestamp=now,
            reason=reason,
            agent_card_synced=synced,
            status="SUCCESS"
        )

        self._record_history(receipt)
        return receipt

    def _record_history(self, receipt: RollbackReceipt):
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append(receipt.model_dump())
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def get_history(self, skill_name: Optional[str] = None) -> List[RollbackReceipt]:
        """ロールバック履歴を取得します。"""
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            receipts = [RollbackReceipt(**item) for item in data]
            if skill_name:
                return [r for r in receipts if r.skill_name == skill_name]
            return receipts
        except Exception:
            return []
