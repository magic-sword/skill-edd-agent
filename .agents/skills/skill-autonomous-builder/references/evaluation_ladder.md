# 3-Tier 品質保証ラダー (The Read / Draft / Act Ladder)

本ドキュメントは、Google 『Agent Skills』ホワイトペーパー（May 2026）Section 4（Page 26）および Appendix B（Page 58）に準拠した、スキルの品質保証および昇格ラダーの単一真実源（SSOT）です。

---

## 品質防壁の基本思想 (The Core Principle)

白書 Page 26 に記されている通り：
> *「隔離されたテスト（In Isolation）での成功は、本番レディネスにおける偽陽性（False Positive）である。」*
> *「本番環境では 5〜15 のスキルが同時マウントされ、相互に注意の奪い合い（Attention Competition）が発生する。」*

そのため、スキルは以下の厳格な 3 段階の権限ラダー（Tiers of Authority）を通じて段階的に昇格（Graduate）させなければなりません。

---

## 昇格基準マトリクス

| Tier レベル | 権限・ケイパビリティ | 必須検証要件 (Graduation Requirements) | 昇格コマンド |
| :--- | :--- | :--- | :--- |
| **Tier 1: Read-Only** | データの参照・取得・要約のみ可能。<br>状態変更は不可。 | 1. 静的検証（`edd validate`）エラー・警告 0 件<br>2. CLI 契約テスト 100% パス<br>3. トリガー精度 90% 以上 (3正例+3負例) | `edd optimize <skill> --tier 1` |
| **Tier 2: Draft-Only** | 下書き・ドラフトの作成が可能。<br>本番適用には人間のレビューを要する。 | 1. Tier 1 要件の全充足<br>2. ゴールデンデータセット（20+ ケース）評価 90% 以上<br>3. 依存関係グラフ（DAG）に基づく連鎖回帰テスト（Cascade Testing）100% パス | `edd optimize <skill> --tier 2` |
| **Tier 3: Action-Allowed** | 不可逆な本番操作（ファイル上書き、外部送信、システム変更等）の実行を許可。 | 1. Tier 2 要件の全充足<br>2. $pass^k$ 持続的信頼性検証（$k \ge 3$ 連続成功）<br>3. Co-loaded 共存負荷テスト（5〜15スキル共存下での精度維持）<br>4. **人間の明示的承認（Human Sign-off: `--yes`）** | `edd optimize <skill> --tier 3 --yes` |

---

## $pass^k$ (Sustained Reliability) 仕様

1 回のラッキー合格（$pass@1$）は本番環境の信頼性を保証しません（tau-bench 研究において GPT-4o は $pass^1$ 61% から $pass^8$ で 25% 未満へ急落）。
本エコシステムでは、指定された $k$ 回連続実行で全勝を要求する $pass^k$ 検証を Tier 3 昇格の必須条件とします。
