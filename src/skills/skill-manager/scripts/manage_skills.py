#!/usr/bin/env python3
"""
スキルのTierおよびメタデータを一括管理するためのCLIツール。
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing.cli import SkillCommandLineRunner


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "skills_registry.json"))
SKILLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

def load_registry(registry_path=None):
    path = registry_path or DEFAULT_REGISTRY_PATH
    if not os.path.exists(path):
        return {"skills": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading registry: {e}", file=sys.stderr)
        return {"skills": {}}

def save_registry(registry, registry_path=None):
    path = registry_path or DEFAULT_REGISTRY_PATH
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving registry: {e}", file=sys.stderr)

def calculate_skill_hashes(skill_name):
    skill_dir = os.path.join(SKILLS_DIR, skill_name)
    hashes = {}
    if not os.path.exists(skill_dir):
        return hashes
    for root, _, files in os.walk(skill_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, skill_dir)
            if "__pycache__" in rel_path or rel_path.endswith(".pyc") or ".git" in rel_path:
                continue
            hasher = hashlib.sha256()
            try:
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
                hashes[rel_path] = hasher.hexdigest()
            except Exception:
                pass
    return hashes

def register_skill(skill_name, registry_path=None):
    registry = load_registry(registry_path)
    if skill_name in registry["skills"]:
        print(f"Skill '{skill_name}' already registered.")
        return
    
    hashes = calculate_skill_hashes(skill_name)
    registry["skills"][skill_name] = {
        "tier": 1,  # デフォルトは Tier 1 (Read-Only)
        "last_tested": None,
        "file_hashes": hashes
    }
    save_registry(registry, registry_path)
    print(f"Registered skill '{skill_name}' at Tier 1.")

def set_tier(skill_name, tier, registry_path=None):
    if tier not in [0, 1, 2, 3]:
        print("Error: Tier must be 0, 1, 2, or 3.", file=sys.stderr)
        sys.exit(1)
    registry = load_registry(registry_path)
    
    now_str = datetime.datetime.now().isoformat() + "Z"
    if skill_name not in registry["skills"]:
        registry["skills"][skill_name] = {
            "tier": tier,
            "last_tested": now_str,
            "file_hashes": calculate_skill_hashes(skill_name)
        }
    else:
        registry["skills"][skill_name]["tier"] = tier
        registry["skills"][skill_name]["last_tested"] = now_str
        registry["skills"][skill_name]["file_hashes"] = calculate_skill_hashes(skill_name)
        
    save_registry(registry, registry_path)
    print(f"Set tier of '{skill_name}' to {tier}.")

def list_skills(registry_path=None):
    registry = load_registry(registry_path)
    print(f"{'Skill Name':<25} | {'Tier':<5} | {'Last Tested':<25}")
    print("-" * 63)
    for name, info in sorted(registry["skills"].items()):
        last_tested = info.get("last_tested") or "Never"
        print(f"{name:<25} | {info['tier']:<5} | {last_tested:<25}")

def update_meta(skill_name, registry_path=None):
    registry = load_registry(registry_path)
    if skill_name not in registry["skills"]:
        register_skill(skill_name, registry_path)
        return
    
    hashes = calculate_skill_hashes(skill_name)
    registry["skills"][skill_name]["file_hashes"] = hashes
    save_registry(registry, registry_path)
    print(f"Updated file hashes for skill '{skill_name}'.")

def manage_skills_logic(tool_context: ToolContext):
    """スキル登録・管理のメインビジネスロジック"""
    command = tool_context.state.get("command")
    skill_name = tool_context.state.get("skill_name")
    tier = tool_context.state.get("tier")
    registry_path = tool_context.state.get("registry_path")

    if not command:
        raise ValueError("Error: 'command' is required.")

    if registry_path:
        registry_path = os.path.abspath(registry_path)
    else:
        registry_path = DEFAULT_REGISTRY_PATH

    status = "success"
    message = ""
    result_data = {}

    try:
        if command == "register":
            if not skill_name:
                raise ValueError("skill_name is required")
            register_skill(skill_name, registry_path)
            message = f"Registered skill '{skill_name}' at Tier 1."
        elif command == "get-tier":
            if not skill_name:
                raise ValueError("skill_name is required")
            registry = load_registry(registry_path)
            skill_info = registry["skills"].get(skill_name)
            current_tier = skill_info["tier"] if skill_info else 1
            print(current_tier)
            result_data["tier"] = current_tier
            message = f"Got tier {current_tier} for skill '{skill_name}'."
        elif command == "set-tier":
            if not skill_name or tier is None:
                raise ValueError("skill_name and tier are required")
            try:
                tier = int(tier)
            except ValueError:
                pass
            set_tier(skill_name, tier, registry_path)
            message = f"Set tier of '{skill_name}' to {tier}."
        elif command == "list":
            list_skills(registry_path)
            message = "Listed all skills."
        elif command == "update-meta":
            if not skill_name:
                raise ValueError("skill_name is required")
            update_meta(skill_name, registry_path)
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
        
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "success",
            "message": f"Set tier of '{skill_name}' to {tier}.",
            "skill_name": skill_name
        }, f, indent=2, ensure_ascii=False)
        
    tool_context.state["reg_out_json_path"] = output_json_path
    
    return f"Success: Set tier of '{skill_name}' to {tier}."

if __name__ == "__main__":
    runner = SkillCommandLineRunner(description="Skill Tier Registry Manager CLI")
    runner.add_argument("--command", choices=["register", "get-tier", "set-tier", "list", "update-meta"], required=True, help="Command to execute")
    runner.add_argument("--skill_name", help="Name of the skill")
    runner.add_argument("--tier", type=int, choices=[0, 1, 2, 3], help="Tier value (0, 1, 2, 3)")
    runner.add_argument("--registry_path", help="Path to skills_registry.json file")
    runner.run(manage_skills_logic)
