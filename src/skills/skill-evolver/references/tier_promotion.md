# Tier 昇格防壁仕様 (Tier Promotion Gates)

## Tier 定義と昇格要件

| Tier レベル | 名称 | 必須要件 | 昇格コマンド |
| :--- | :--- | :--- | :--- |
| **Tier 0** | DRAFT | なし（初期作成状態） | - |
| **Tier 1** | READ_ONLY (Production) | 静的検証合格 + 契約テスト 100% + トリガーテスト 90% | `edd tier-gate <skill> --tier 1` |
| **Tier 2** | VERIFIED | Tier 1 要件 + ゴールデン 90% + 連鎖回帰テスト合格 | `edd tier-gate <skill> --tier 2` |
| **Tier 3** | MASTERED | Tier 2 要件 + 敵対的テスト 100% + 履歴安定性 | `edd tier-gate <skill> --tier 3` |
