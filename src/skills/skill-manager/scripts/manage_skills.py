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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# /workspace/src/skills/skill-manager/scripts -> /workspace/src/skills_registry.json
REGISTRY_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "skills_registry.json"))
SKILLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        return {"skills": {}}
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading registry: {e}", file=sys.stderr)
        return {"skills": {}}

def save_registry(registry):
    try:
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
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
            # キャッシュファイルなどは除外
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

def register_skill(skill_name):
    registry = load_registry()
    if skill_name in registry["skills"]:
        print(f"Skill '{skill_name}' already registered.")
        return
    
    hashes = calculate_skill_hashes(skill_name)
    registry["skills"][skill_name] = {
        "tier": 1,  # デフォルトは Tier 1 (Read-Only)
        "last_tested": None,
        "file_hashes": hashes
    }
    save_registry(registry)
    print(f"Registered skill '{skill_name}' at Tier 1.")

def get_tier(skill_name):
    registry = load_registry()
    skill_info = registry["skills"].get(skill_name)
    if not skill_info:
        # 未登録スキルの場合は一時的に Tier 1 とみなして出力
        print("1")
        return
    print(skill_info["tier"])

def set_tier(skill_name, tier):
    if tier not in [1, 2, 3]:
        print("Error: Tier must be 1, 2, or 3.", file=sys.stderr)
        sys.exit(1)
    registry = load_registry()
    
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
        
    save_registry(registry)
    print(f"Set tier of '{skill_name}' to {tier}.")

def list_skills():
    registry = load_registry()
    print(f"{'Skill Name':<25} | {'Tier':<5} | {'Last Tested':<25}")
    print("-" * 63)
    for name, info in sorted(registry["skills"].items()):
        last_tested = info.get("last_tested") or "Never"
        print(f"{name:<25} | {info['tier']:<5} | {last_tested:<25}")

def update_meta(skill_name):
    registry = load_registry()
    if skill_name not in registry["skills"]:
        register_skill(skill_name)
        return
    
    hashes = calculate_skill_hashes(skill_name)
    registry["skills"][skill_name]["file_hashes"] = hashes
    save_registry(registry)
    print(f"Updated file hashes for skill '{skill_name}'.")

def main():
    parser = argparse.ArgumentParser(description="Skill Tier Registry Manager CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # register
    reg_parser = subparsers.add_parser("register", help="Register a new skill")
    reg_parser.add_argument("skill_name", help="Name of the skill")
    
    # get-tier
    get_parser = subparsers.add_parser("get-tier", help="Get current tier of a skill")
    get_parser.add_argument("skill_name", help="Name of the skill")
    
    # set-tier
    set_parser = subparsers.add_parser("set-tier", help="Set tier of a skill")
    set_parser.add_argument("skill_name", help="Name of the skill")
    set_parser.add_argument("tier", type=int, choices=[1, 2, 3], help="Tier value (1, 2, 3)")
    
    # list
    subparsers.add_parser("list", help="List all registered skills")
    
    # update-meta
    meta_parser = subparsers.add_parser("update-meta", help="Update file hashes and metadata of a skill")
    meta_parser.add_argument("skill_name", help="Name of the skill")
    
    args = parser.parse_args()
    
    if args.command == "register":
        register_skill(args.skill_name)
    elif args.command == "get-tier":
        get_tier(args.skill_name)
    elif args.command == "set-tier":
        set_tier(args.skill_name, args.tier)
    elif args.command == "list":
        list_skills()
    elif args.command == "update-meta":
        update_meta(args.skill_name)

if __name__ == "__main__":
    main()
