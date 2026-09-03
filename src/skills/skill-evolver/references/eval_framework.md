# 多層評価フレームワーク仕様 (Evaluation Framework)

Google 『Agent Skills』ホワイトペーパー（May 2026）および Google ADK 2.0 純正評価フレームワーク準拠の評価仕様です。

---

## 評価テストの種類と CLI オプション

| テスト種類 (`--type`) | 主な検証内容 | 合格基準 | 推奨 CLI オプション |
| :--- | :--- | :--- | :--- |
| **`--coverage`** | 白書 Section 4 の 4大 Eval Coverage Checklist (Trigger, Execution, Regression, Token Budget) | 100% | `edd eval <skill> --coverage` |
| **`edd`** | Google ADK 2.0 公式 EvalSet 準拠の複合評価 (Trigger + 3大 Trajectory + Rubric) | 100% | `edd eval <skill> -t edd` |
| **`contract`** | CLI引数・終了コード・出力形式の Black-box 実行 | 100% | `edd eval <skill> -t contract --pass-k 3` |
| **`trigger`** | ユーザー発話に対するインテント判定（正例3件・負例3件） | 90% 以上 | `edd eval <skill> -t trigger` |
| **`trajectory`** | ADK 2.0 純正 TrajectoryEvaluator による軌跡（`EXACT` / `IN_ORDER` / `ANY_ORDER`） | 100% | `edd eval <skill> -t trajectory --trajectory-mode in_order` |
| **`golden`** | 複合環境設定・エッジケースの出力完全性アサーション | 90% 以上 | `edd eval <skill> -t golden` |
| **`judge`** | Google ADK 純正 `RubricBasedFinalResponseQualityV1Evaluator` によるルーブリック採点 | 85% 以上 | `edd eval <skill> -t judge` |
| **`adk-eval`** | Google ADK 2.0 公式 `AgentEvaluator.evaluate()` の直接ワンストップ実行 | 100% | `edd adk-eval <skill>` |
| **`co-loaded`** | 5〜15 スキル同時展開下での Context Rot 防止ベンチマーク | 80% 以上 | `edd eval <skill> --co-loaded` |
| **`all`** | 全評価テストスイートの一括総合実行 | 100% | `edd eval <skill> -t all` |

