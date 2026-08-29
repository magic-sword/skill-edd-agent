#!/usr/bin/env python3
"""
skill-planner のメインエントリポイント。
エージェント向け公開関数および CLI を提供。
"""

import sys
import argparse
from pathlib import Path
try:
    from .planner import (
        plan_skill_development,
        SkillPlanner,
        SkillPlannerOutput,
        ProposedSkill
    )
except (ImportError, ValueError):
    from planner import (
        plan_skill_development,
        SkillPlanner,
        SkillPlannerOutput,
        ProposedSkill
    )

# 後方互換エイリアス
skill_planner = plan_skill_development

__all__ = [
    "plan_skill_development",
    "skill_planner",
    "SkillPlanner",
    "SkillPlannerOutput",
    "ProposedSkill"
]


def main():
    parser = argparse.ArgumentParser(description="Skill Planner CLI Entrypoint")
    parser.add_argument("prompt", type=str, nargs="?", default="", help="Natural language requirement prompt")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to save output planning JSON")
    args = parser.parse_args()

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    res = plan_skill_development(prompt=args.prompt)
    out_json = res.model_dump_json(indent=2)

    if args.output:
        Path(args.output).write_text(out_json, encoding="utf-8")
        print(f"✅ Saved planning result to: {args.output}")
    else:
        print(out_json)


if __name__ == "__main__":
    main()
