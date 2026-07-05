#!/usr/bin/env python3
"""
スキルのTierおよびメタデータを一括管理するためのCLIツール。
"""
import argparse
import os
import sys
import json
from google.adk.tools import ToolContext

from edd_agent_tools.registry import SkillRegistry


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "skills_registry.json"))

def manage_skills_logic(tool_context: ToolContext):
    """スキル登録・管理のメインビジネスロジック"""
    command = tool_context.state.get("command")
    skill = tool_context.state.get("skill")
    tier = tool_context.state.get("tier")
    registry_path = tool_context.state.get("registry_path") or DEFAULT_REGISTRY_PATH

    if not command:
        raise ValueError("Error: 'command' is required.")

    status = "success"
    message = ""
    result_data = {}

    # パッケージの SkillRegistry を使用
    registry = SkillRegistry(registry_path=registry_path)

    try:
        if command == "register":
            if not skill:
                raise ValueError("skill is required")
            registered = registry.register_skill(skill)
            if registered:
                message = f"Registered skill '{skill}' at Tier 0."
            else:
                skill_info = registry.get_skill_info(skill)
                current_tier = skill_info.tier if skill_info else 0
                message = f"Skill '{skill}' already registered at Tier {current_tier}."
        elif command == "get-tier":
            if not skill:
                raise ValueError("skill is required")
            skill_info = registry.get_skill_info(skill)
            current_tier = skill_info.tier if skill_info else 1
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
            updated = registry.set_tier(skill, tier)
            if updated:
                message = f"Set tier of '{skill}' to {tier}."
            else:
                skill_info = registry.get_skill_info(skill)
                current_tier = skill_info.tier if skill_info else 0
                message = f"Skipped promotion to Tier {tier} for '{skill}' (current tier is {current_tier})."
        elif command == "list":
            registry.list_skills()
            message = "Listed all skills."
        elif command == "update-meta":
            if not skill:
                raise ValueError("skill is required")
            registry.update_meta(skill)
            message = f"Updated metadata for skill '{skill}'."
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

def set_skill_tier(command: str, tier: int, tool_context: ToolContext) -> str:
    """
    指定されたスキルのTierを設定・更新します。
    """
    # セッション状態を更新して共通ロジックに流す
    tool_context.state["command"] = command
    tool_context.state["tier"] = tier
    
    skill = tool_context.state.get("skill")
    
    manage_skills_logic(tool_context)
    
    # ワークフロー固有の一時ファイル出力 (互換性のため)
    output_json_path = f"/workspace/src/.workflow_tmp/{skill}/01_reg_out.json"
    if tier == 1:
        output_json_path = f"/workspace/src/.workflow_tmp/{skill}/07_final_reg_out.json"
        
    final_message = tool_context.state.get("message", f"Set tier of '{skill}' to {tier}.")
        
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": tool_context.state.get("status", "success"),
            "message": final_message,
            "skill": skill
        }, f, indent=2, ensure_ascii=False)
        
    tool_context.state["reg_out_json_path"] = output_json_path
    
    return f"Success: {final_message}"
