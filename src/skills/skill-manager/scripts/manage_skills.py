#!/usr/bin/env python3
"""
スキルのTierおよびメタデータを一括管理するためのCLIツール。
"""
import argparse
import os
import sys
import json
from google.adk.tools import ToolContext
from edd_agent_tools.skills import SkillsState, SkillTier
from .models import Input


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATE_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "skills_state.json"))

def manage_skills_logic(params: Input, tool_context: ToolContext) -> str:
    """スキル登録・管理のメインビジネスロジック"""
    command = params.command
    skill = params.skill
    tier = params.tier
    state_path = params.registry_path or DEFAULT_STATE_PATH

    if not command:
        raise ValueError("Error: 'command' is required.")

    status = "success"
    message = ""
    result_data = {}

    # パッケージの SkillsState を使用
    state = SkillsState(state_path=state_path)

    try:
        if command == "register":
            if not skill:
                raise ValueError("skill is required")
            skill_obj = state.get_skill(skill)
            registered = state.register_skill(skill_obj)
            if registered:
                message = f"Registered skill '{skill}'."
            else:
                current_tier = skill_obj.metadata.tier if skill_obj else 0
                message = f"Skill '{skill}' already registered or skipped (tier: {current_tier})."
        elif command == "get-tier":
            if not skill:
                raise ValueError("skill is required")
            skill_obj = state.get_skill(skill)
            current_tier = skill_obj.metadata.tier if skill_obj else 1
            print(current_tier)
            result_data["tier"] = current_tier
            message = f"Got tier {current_tier} for skill/agent '{skill}'."
        elif command == "set-tier":
            if not skill or tier is None:
                raise ValueError("skill and tier are required")
            try:
                tier = int(tier)
            except ValueError:
                pass
            skill_obj = state.get_skill(skill)
            skill_obj.set_tier(tier)
            updated = state.register_skill(skill_obj)
            if updated:
                message = f"Set tier of '{skill}' to {tier}."
            else:
                current_tier = skill_obj.metadata.tier if skill_obj else 0
                message = f"Skipped promotion to Tier {tier} for '{skill}' (current tier is {current_tier})."
        elif command == "list":
            skills = state.list_skills()
            print(f"{'Category':<10} | {'Name':<25} | {'Tier':<5} | {'Last Tested':<25}")
            print("-" * 75)
            from edd_agent_tools.models import ModuleType
            for skill_obj in sorted(skills, key=lambda s: (s.metadata.module_type, s.name)):
                cat = "Agent" if skill_obj.metadata.module_type == ModuleType.WORKFLOW else "Skill"
                last_tested = skill_obj.metadata.last_tested or "Never"
                print(f"{cat:<10} | {skill_obj.name:<25} | {skill_obj.metadata.tier:<5} | {last_tested:<25}")
            message = "Listed all skills."
        elif command == "update-meta":
            if not skill:
                raise ValueError("skill is required")
            # registry.update_meta は廃止されたため、非推奨警告メッセージの返却のみ行います
            message = f"Skipped: 'update-meta' command is deprecated and no-op (hashes are fully removed)."
        else:
            raise ValueError(f"Unknown command: {command}")
    except Exception as e:
        status = "failed"
        message = str(e)
        print(f"Error executing command: {e}", file=sys.stderr)

    # 共通の出力状態のセット
    tool_context.state.update({
        "status": status,
        "message": message,
        "skill": skill,
        **result_data
    })

    if status != "success":
        raise RuntimeError(message)

    return message
