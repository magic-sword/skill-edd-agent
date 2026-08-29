#!/usr/bin/env python3
"""
skill-evaluator のメインエントリポイント (CLI & Python API)
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional

from generate_evalset import generate_evalset
from run_eval import run_evaluation
from run_tier_gate import run_tier_gate


def evaluate_skill(
    skill_name: str,
    action: str = "gate",
    target_tier: int = 1,
    test_type: str = "all",
    eval_set_path: Optional[str] = None
) -> Dict[str, Any]:
    """スキルの評価パイプラインを実行する統合関数。

    Args:
        skill_name: 評価対象スキル名。
        action: 'generate' (テスト生成), 'run' (評価実行), 'gate' (Tier昇格判定)。
        target_tier: 昇格目標Tier (1, 2, 3)。
        test_type: テスト種別 ('trigger', 'contract', 'golden', 'judge', 'all')。
        eval_set_path: 個別の評価セットJSONパス（省略時は自動解決）。

    Returns:
        Dict[str, Any]: 実行結果。
    """
    if action == "generate":
        return generate_evalset(skill_name, test_type=test_type)
    elif action == "run":
        return run_evaluation(skill_name, test_type=test_type, eval_set_path=eval_set_path)
    elif action == "gate":
        return run_tier_gate(skill_name, target_tier=target_tier)
    else:
        return {"status": "failed", "message": f"Unknown action '{action}'"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill Evaluator CLI")
    parser.add_argument("skill_name", help="Name of the target skill")
    parser.add_argument("--action", choices=["generate", "run", "gate"], default="gate", help="Action to perform")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier for gate action")
    parser.add_argument("--type", choices=["trigger", "contract", "golden", "judge", "all"], default="all", help="Test type")

    args = parser.parse_args()
    res = evaluate_skill(args.skill_name, action=args.action, target_tier=args.tier, test_type=args.type)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("status") == "success" else 1)
