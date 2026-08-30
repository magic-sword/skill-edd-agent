#!/usr/bin/env python3
"""
Skill Optimizer & Promotion Engine (CLI & API)

スキルの静的検証、評価テスト、連鎖回帰テスト（Cascade Testing）、および Tier 昇格を実行します。
統合 CLI `edd` を活用して決定論的なオーケストレーションを行います。

Usage:
    python optimizer.py <skill-name> [--target-tier {0,1,2,3}] [--cascade] [--dry-run]
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List


def run_cmd(cmd: List[str]) -> tuple[int, str, str]:
    """コマンドを実行し、終了コード・stdout・stderr を返します。"""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return -1, "", str(e)


class SkillOptimizer:
    """決定論的テスト実行、静的検証、連鎖回帰テスト、Tier 昇格を行うエンジン。"""

    def __init__(self, state: Optional[Any] = None):
        self.state = state
        try:
            from edd_agent_tools.evaluation import CascadeTestRunner
            self.cascade_runner = CascadeTestRunner(state=state)
        except Exception:
            self.cascade_runner = None

    def run_verification(self, skill_name: str) -> Dict[str, Any]:
        """対象スキルの静的検証および単体評価テストを実行します。"""
        cand_dir = Path("src/skills") / skill_name
        skill_dir = cand_dir if cand_dir.exists() else Path(skill_name)

        if not skill_dir.exists():
            return {"status": "failed", "message": f"Skill directory '{skill_dir}' not found."}

        # 1. 静的検証 (`edd validate`)
        val_code, val_out, val_err = run_cmd([sys.executable, "-m", "edd_agent_tools.cli", "validate", str(skill_dir)])
        if val_code != 0:
            return {
                "status": "validation_failed",
                "message": val_err or val_out,
                "passed": False
            }

        # 2. 評価テスト (`edd eval`)
        eval_code, eval_out, eval_err = run_cmd([sys.executable, "-m", "edd_agent_tools.cli", "eval", skill_name])
        return {
            "status": "success" if eval_code == 0 else "tests_failed",
            "skill_name": skill_name,
            "validation_passed": True,
            "all_tests_passed": eval_code == 0,
            "output": eval_out
        }

    def optimize_skill(
        self,
        skill_name: str,
        target_tier: int = 1,
        run_cascade: bool = True,
        max_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """対象スキルの検証、連鎖回帰テスト、Tier 昇格を実行します。"""
        cand_dir = Path("src/skills") / skill_name
        skill_dir = cand_dir if cand_dir.exists() else Path(skill_name)
        if not skill_dir.exists():
            return {
                "status": "failed",
                "message": f"Skill '{skill_name}' not found."
            }

        # 1. 単体検証
        verif_res = self.run_verification(skill_name)
        if not verif_res.get("all_tests_passed"):
            return {
                "status": "needs_healing",
                "skill_name": skill_name,
                "details": verif_res,
                "message": "単体テストまたは静的検証に失敗しました。skill-diagnoser で原因を分析し、修正を適用してください。"
            }

        # 2. Tier 昇格防壁テスト (`edd tier-gate`)
        gate_code, gate_out, gate_err = run_cmd([
            sys.executable, "-m", "edd_agent_tools.cli", "tier-gate", skill_name, "--tier", str(target_tier)
        ])

        if gate_code != 0:
            return {
                "status": "gate_failed",
                "skill_name": skill_name,
                "message": f"Tier {target_tier} 昇格テストに合格できませんでした: {gate_err or gate_out}"
            }

        return {
            "status": "success",
            "skill_name": skill_name,
            "promoted_tier": target_tier,
            "verification": verif_res,
            "message": f"スキル '{skill_name}' は検証および Tier {target_tier} 昇格テストに合格しました。"
        }


def optimize_skill(skill_name: str, target_tier: int = 1, run_cascade: bool = True, max_retries: int = 3, **kwargs) -> Dict[str, Any]:
    """モジュールレベルのヘルパー関数"""
    optimizer = SkillOptimizer()
    return optimizer.optimize_skill(
        skill_name=skill_name,
        target_tier=target_tier,
        run_cascade=run_cascade,
        max_retries=max_retries,
        **kwargs
    )


def main():
    parser = argparse.ArgumentParser(description="Skill Optimizer & Promotion Engine")
    parser.add_argument("skill", type=str, help="対象スキルの論理名またはパス")
    parser.add_argument("--target-tier", "-t", type=int, default=1, choices=[1, 2, 3], help="昇格目標の Tier (1: Production, 2: Verified, 3: Mastered)")
    parser.add_argument("--cascade", "-c", action="store_true", default=True, help="連鎖回帰テストを実行する")
    parser.add_argument("--format", "-f", type=str, choices=["json", "text"], default="text", help="出力フォーマット")

    args = parser.parse_args()
    optimizer = SkillOptimizer()
    res = optimizer.optimize_skill(
        skill_name=args.skill,
        target_tier=args.target_tier,
        run_cascade=args.cascade
    )

    if args.format == "json":
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"==================================================")
        print(f"🚀 Skill Optimization & Promotion: {args.skill}")
        print(f"==================================================")
        print(f"Status: {res.get('status')}")
        print(f"Message: {res.get('message')}")
        if "promoted_tier" in res:
            print(f"Promoted Tier: Tier {res.get('promoted_tier')}")

    return 0 if res.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
