#!/usr/bin/env python3
"""
スキルのTierおよびメタデータを一括管理するためのCLIツール。
"""
import argparse
import os
import sys
import json
from google.adk.tools import ToolContext
from edd_agent_tools.testing import SkillCommandLineRunner
from edd_agent_tools.registry import SkillRegistry


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "skills_registry.json"))

def manage_skills_logic(tool_context: ToolContext):
    """スキル登録・管理のメインビジネスロジック"""
    command = tool_context.state.get("command")
    skill_name = tool_context.state.get("skill_name")
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
            if not skill_name:
                raise ValueError("skill_name is required")
            registered = registry.register_skill(skill_name)
            if registered:
                message = f"Registered skill '{skill_name}' at Tier 0."
            else:
                registry_data = registry.load()
                skill_info = registry_data.get("skills", {}).get(skill_name) or registry_data.get("agents", {}).get(skill_name)
                current_tier = skill_info["tier"] if skill_info else 0
                message = f"Skill '{skill_name}' already registered at Tier {current_tier}."
        elif command == "get-tier":
            if not skill_name:
                raise ValueError("skill_name is required")
            registry_data = registry.load()
            skill_info = registry_data.get("skills", {}).get(skill_name) or registry_data.get("agents", {}).get(skill_name)
            current_tier = skill_info["tier"] if skill_info else 1
            print(current_tier)
            result_data["tier"] = current_tier
            message = f"Got tier {current_tier} for skill/agent '{skill_name}'."
        elif command == "set-tier":
            if not skill_name or tier is None:
                raise ValueError("skill_name and tier are required")
            try:
                tier = int(tier)
            except ValueError:
                pass
            updated = registry.set_tier(skill_name, tier)
            if updated:
                message = f"Set tier of '{skill_name}' to {tier}."
            else:
                registry_data = registry.load()
                skill_info = registry_data.get("skills", {}).get(skill_name) or registry_data.get("agents", {}).get(skill_name)
                current_tier = skill_info["tier"] if skill_info else 0
                message = f"Skipped promotion to Tier {tier} for '{skill_name}' (current tier is {current_tier})."
        elif command == "list":
            registry.list_skills()
            message = "Listed all skills."
        elif command == "update-meta":
            if not skill_name:
                raise ValueError("skill_name is required")
            registry.update_meta(skill_name)
            message = f"Updated metadata for skill '{skill_name}'."
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
        "skill_name": skill_name,
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
    
    skill_name = tool_context.state.get("skill_name")
    
    manage_skills_logic(tool_context)
    
    # ワークフロー固有の一時ファイル出力 (互換性のため)
    output_json_path = f"/workspace/src/.workflow_tmp/{skill_name}/01_reg_out.json"
    if tier == 1:
        output_json_path = f"/workspace/src/.workflow_tmp/{skill_name}/07_final_reg_out.json"
        
    final_message = tool_context.state.get("message", f"Set tier of '{skill_name}' to {tier}.")
        
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": tool_context.state.get("status", "success"),
            "message": final_message,
            "skill_name": skill_name
        }, f, indent=2, ensure_ascii=False)
        
    tool_context.state["reg_out_json_path"] = output_json_path
    
    return f"Success: {final_message}"
