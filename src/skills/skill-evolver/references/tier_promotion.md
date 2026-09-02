# Tier 昇格防壁仕様 (Tier Promotion Gates)

Google 『Agent Skills』ホワイトペーパー（May 2026）準拠の 3 段階権限ラダー（The Read / Draft / Act Ladder）です。

---

## Tier 定義と昇格要件

| Tier レベル | 名称 | 必須要件 | 昇格コマンド |
| :--- | :--- | :--- | :--- |
| **Tier 0** | **`DRAFT`** | 初期作成状態（未検証） | - |
| **Tier 1** | **`READ_ONLY`** (Production) | 静的検証合格（`edd validate` エラー/警告0） + 契約テスト 100% + トリガー精度 90% 以上 | `edd tier-gate <skill> --tier 1` |
| **Tier 2** | **`DRAFT_ONLY`** (Verified) | Tier 1 要件 + ゴールデン 90% 以上 + 上位依存スキルの連鎖回帰テスト（Cascade Regression 100% パス） | `edd tier-gate <skill> --tier 2` |
| **Tier 3** | **`ACTION_ALLOWED`** (Mastered) | Tier 2 要件 + Tool Trajectory 評価（`IN_ORDER` / `EXACT`） + $pass^k$ 持続的一貫性（$k \ge 3$） + Co-loaded 共存テスト + **人間の明示的承認 (Human Sign-off)** | `edd tier-gate <skill> --tier 3 --yes` |
