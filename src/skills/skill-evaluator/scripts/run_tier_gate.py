#!/usr/bin/env python3
"""
Tier Promotion Gatekeeper (CLI & API)

Tier 1 (Production), Tier 2 (Verified), Tier 3 (Mastered) の昇格防壁テストを実行し、
合否判定およびステータス昇格を管理します。

Usage:
    python run_tier_gate.py <skill_name> [--tier {1,2,3}]
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def run_tier_gate(
    skill_name: str,
    target_tier: int = 1,
    eval_set_base_path: str = "tests"
) -> Dict[str, Any]:
    """対象スキルの Tier 昇格防壁テストを実行し、合否判定・ステータス更新を行います。"""
    # 1. 統合 CLI `edd tier-gate` を呼び出し
    cmd = [sys.executable, "-m", "edd_agent_tools.cli", "tier-gate", skill_name, "--tier", str(target_tier)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return {
                "status": "success",
                "message": proc.stdout.strip(),
                "promoted_tier": target_tier
            }
        else:
            return {
                "status": "failed",
                "message": proc.stderr.strip() or proc.stdout.strip()
            }
    except Exception as e:
        return {"status": "failed", "message": f"CLI execution error: {e}"}


def main():
    parser = argparse.ArgumentParser(description="Run tier promotion gatekeeper for a skill")
    parser.add_argument("skill_name", help="Name of the skill to promote")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier level (1: Production, 2: Verified, 3: Mastered)")
    parser.add_argument("--evalset-base", default="tests", help="Base path to search for evalset files")

    args = parser.parse_args()
    res = run_tier_gate(args.skill_name, target_tier=args.tier, eval_set_base_path=args.evalset_base)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
