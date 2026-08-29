try:
    from .optimizer import SkillOptimizer
except (ImportError, ValueError):
    from optimizer import SkillOptimizer

def optimize_skill(skill_name: str, max_retries: int = 3) -> dict:
    """テスト失敗検知 ➔ 診断 ➔ 3層リソース差分修正 ➔ 再テスト ➔ 連鎖回帰テストの自律改善ループを実行します。

    Args:
        skill_name: 最適化・改善対象のスキル名。
        max_retries: 最大修正試行回数。

    Returns:
        dict: 改善処理の実行結果サマリー。
    """
    optimizer = SkillOptimizer()
    return optimizer.optimize_skill(skill_name=skill_name, max_retries=max_retries)


if __name__ == "__main__":
    import sys
    import json
    import argparse

    parser = argparse.ArgumentParser(description="Skill Optimizer Entrypoint CLI")
    parser.add_argument("skill", type=str, nargs="?", default="", help="Logical name of the target skill (e.g. pdf-tools)")
    parser.add_argument("--retries", "-r", type=int, default=3, help="Max retry iterations (default: 3)")
    args = parser.parse_args()

    if not args.skill:
        parser.print_help()
        sys.exit(1)

    res = optimize_skill(skill_name=args.skill, max_retries=args.retries)
    print(json.dumps(res, indent=2, ensure_ascii=False))

