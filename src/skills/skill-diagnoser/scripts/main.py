#!/usr/bin/env python3
"""
skill-diagnoser のメインエントリポイント。
エージェント向け公開関数および CLI を提供。
"""

import sys
import argparse
from typing import Optional
try:
    from .diagnoser import (
        diagnose_skill_failure,
        SkillDiagnoser,
        DiagnoseSkillFailureOutput,
        ImprovementPlan,
        TargetLayer,
        FailureCategory
    )
except (ImportError, ValueError):
    from diagnoser import (
        diagnose_skill_failure,
        SkillDiagnoser,
        DiagnoseSkillFailureOutput,
        ImprovementPlan,
        TargetLayer,
        FailureCategory
    )

__all__ = [
    "diagnose_skill_failure",
    "SkillDiagnoser",
    "DiagnoseSkillFailureOutput",
    "ImprovementPlan",
    "TargetLayer",
    "FailureCategory"
]


def main():
    parser = argparse.ArgumentParser(description="Skill Diagnoser CLI Entrypoint")
    parser.add_argument("skill", type=str, nargs="?", default="", help="Logical name of the target skill (e.g. pdf-tools)")
    parser.add_argument("--report", "-r", type=str, default=None, help="Path to test report JSON")
    parser.add_argument("--test-type", "-t", type=str, default=None, help="Test type (contract, trigger, etc.)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to save output JSON")
    args = parser.parse_args()

    if not args.skill:
        parser.print_help()
        sys.exit(1)

    res = diagnose_skill_failure(
        skill=args.skill,
        report_path=args.report,
        test_type=args.test_type
    )

    out_json = res.model_dump_json(indent=2)
    if args.output:
        import pathlib
        pathlib.Path(args.output).write_text(out_json, encoding="utf-8")
        print(f"✅ Saved diagnosis result to: {args.output}")
    else:
        print(out_json)


if __name__ == "__main__":
    main()
