"""
Library Evolver Deterministic Pipeline Script (Whitepaper Section 6: Library Evolution Pattern).
Autonomously detects capability gaps, verifies semantic separation, and coordinates skill synthesis and catalog registration.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# edd-agent-tools とは CLI/標準ライブラリ経由で連携
from edd_agent_tools.packaging.scaffold import SkillScaffolder
from edd_agent_tools.packaging.card_sync import AgentCardSynchronizer
from edd_agent_tools.validation.collision import SemanticCollisionDetector
from edd_agent_tools.validation.validator import SkillValidator
from edd_agent_tools.state import SkillsState


class LibraryEvolverPipeline:
    """エージェントのスキルライブラリ自律進化（Voyager型自己増殖）を制御するパイプライン。"""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.state = SkillsState()
        self.collision_detector = SemanticCollisionDetector(state=self.state)
        self.validator = SkillValidator()
        self.card_sync = AgentCardSynchronizer(state=self.state)

    def plan_skill_evolution(
        self,
        target_task_desc: str,
        suggested_skill_name: str,
        pattern: str = "workflow",
    ) -> Dict[str, Any]:
        """ギャップ分析およびセマンティック重複検査を行い、自己進化計画を立案する。"""
        # 1. 衝突検査（Clarity Check）
        collisions = self.collision_detector.detect_collisions(
            target_skill_name=None,
            threshold=0.60
        )
        conflicts = [c for c in collisions if c["skill_1"] == suggested_skill_name or c["skill_2"] == suggested_skill_name]

        # 2. 既存スキルとの照合
        existing_skills = self.state.list_skills()
        exact_match = any(s.name == suggested_skill_name for s in existing_skills)

        if exact_match:
            decision = "EVOLVE_EXISTING"
            reason = f"Skill '{suggested_skill_name}' already exists. Evolve existing skill rather than creating duplicate."
        elif conflicts:
            decision = "MERGE_OR_REFINE"
            reason = f"Semantic collision detected with '{conflicts[0]['skill_1'] if conflicts[0]['skill_2'] == suggested_skill_name else conflicts[0]['skill_2']}'."
        else:
            decision = "SYNTHESIZE_NEW"
            reason = f"No collision found. Skill '{suggested_skill_name}' is a genuine capability gap. Ready for autonomous synthesis."

        return {
            "status": "planned",
            "target_task": target_task_desc,
            "suggested_skill_name": suggested_skill_name,
            "pattern": pattern,
            "decision": decision,
            "reason": reason,
            "conflicts": conflicts,
        }

    def register_and_promote_synthesized_skill(
        self,
        skill_name: str,
        target_tier: int = 1,
    ) -> Dict[str, Any]:
        """新規合成されたスキルの整合性を検証し、カタログ登録・Agent Card 同期を実施する。"""
        skill_dir = self.workspace_root / "src" / "skills" / skill_name
        if not skill_dir.exists():
            return {
                "status": "error",
                "message": f"Skill directory not found: {skill_dir}",
            }

        # 1. 静的検証
        valid_res = self.validator.validate_skill_dir(skill_dir)
        if not valid_res.is_valid:
            return {
                "status": "error",
                "message": f"Skill validation failed: {valid_res.errors}",
            }

        # 2. SkillsState への登録 & Tier 昇格
        self.state.register_skill(
            name=skill_name,
            root_dir=skill_dir,
            tier=target_tier,
        )

        # 3. Agent Card (A2A v1.0.0) 同期
        sync_res = self.card_sync.sync_agent_card()

        return {
            "status": "success",
            "skill_name": skill_name,
            "promoted_tier": target_tier,
            "agent_card_synced": True,
            "total_registered_skills": sync_res.get("skills_count", 0),
            "message": f"Skill '{skill_name}' has been verified, promoted to Tier {target_tier}, and registered to Agent Card.",
        }


def main():
    parser = argparse.ArgumentParser(description="Library Evolver Deterministic Orchestration Script")
    parser.add_argument("--action", choices=["plan", "register"], required=True, help="Evolution pipeline step")
    parser.add_argument("--task", help="Target task description")
    parser.add_argument("--skill-name", required=True, help="Target skill name (kebab-case)")
    parser.add_argument("--pattern", default="workflow", help="Skill pattern template")
    parser.add_argument("--tier", type=int, default=1, help="Target tier for registration")

    args = parser.parse_args()
    pipeline = LibraryEvolverPipeline()

    if args.action == "plan":
        res = pipeline.plan_skill_evolution(
            target_task_desc=args.task or "Generic task",
            suggested_skill_name=args.skill_name,
            pattern=args.pattern,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.action == "register":
        res = pipeline.register_and_promote_synthesized_skill(
            skill_name=args.skill_name,
            target_tier=args.tier,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
