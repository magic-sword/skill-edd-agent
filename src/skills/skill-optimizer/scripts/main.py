from .optimizer import SkillOptimizer

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
