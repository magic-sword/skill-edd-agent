#!/usr/bin/env python3
"""
Skill Initializer CLI - edd-agent-tools パッケージの標準初期化エンジンを呼び出すCLIスクリプト。
単一真実源の原則に基づき、パッケージ側の SkillTemplateEngine と完全に同期します。

Usage:
    init_skill.py <skill-name> --path <path> [--pattern {workflow,task_based,reference,capabilities}]
"""

import sys
import argparse
from pathlib import Path
from edd_agent_tools.skills.cli import init_skill

def main():
    parser = argparse.ArgumentParser(description="Initialize a new skill directory from template.")
    parser.add_argument("name", help="スキル名（lowercase hyphen-case）")
    parser.add_argument("--path", "-p", default="src/skills", help="出力先親ディレクトリ（デフォルト: src/skills）")
    parser.add_argument("--pattern", choices=["workflow", "task_based", "reference", "capabilities"], default="workflow", help="スキル構造パターン")
    args = parser.parse_args()

    skill_dir = init_skill(args.name, path=args.path, pattern=args.pattern)
    if skill_dir:
        print(f"✅ Successfully initialized skill '{args.name}' at: {skill_dir}")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
