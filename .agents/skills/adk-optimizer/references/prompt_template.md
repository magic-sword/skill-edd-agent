# 子セッション (agy) 向けプロンプトテンプレート

あなたは Google ADK 2.0 およびエージェント設計の最高峰スペシャリストです。
本セッションの目的は、プロジェクトを Google ADK 2.0 公式ベストプラクティスに完全適合させ、車輪の再発明や古い設計思想を排除することです。

以下の手順を厳密に実行してください：

---

### ステップ 1: MCP 経由での公式仕様・ベストプラクティス調査
* MCP サーバー `google-developer-knowledge` のツール（`answer_query` または `search_documents`）を呼び出し、Google ADK 2.0 の最新仕様を確認してください。
* 特に調査すべき領域：
  - `SkillToolset` / `SkillRegistry`（Progressive Disclosure、ダイナミック解決）
  - `BaseCodeExecutor` / `LocalSubprocessCodeExecutor`（スクリプト実行基盤、引数展開規約）
  - `AgentEvaluator` / `TrajectoryEvaluator`（`IN_ORDER` 評価）/ `RubricBasedFinalResponseQualityV1Evaluator`
  - `App` コンテナ、`before_agent_callback` / `after_agent_callback`
  - 不要な自前実装（ラッパー、独自Judge、モンキーパッチ）の排除指針

### ステップ 2: コードベース・ドキュメントの客観的監査
* `.agents/skills/adk-optimizer/references/checklist.md` を参照しながら、現在のリポジトリ全体を厳格に監査してください。
* 以下のいずれかに該当する改善対象が存在するか精査してください：
  1. Google ADK 2.0 に公式機能・APIがあるにもかかわらず、プロジェクト側で独自実装・多重ラップ・再発明しているクラス・関数・CLI
  2. 過去の古い設計思想、非推奨引数、不要な後方互換性コードの残存
  3. 公式の Progressive Disclosure やエージェント構成規約に反するプロンプトや設定
  4. 実装の最新化に伴い古くなったドキュメント（`AGENTS.md`, `design_philosophy.md`, `README.md` 等）の記述

---

## ⚠️ 重要：監査結果に基づく排他分岐 (CRITICAL BRANCHING)

ステップ 2 の監査結果に応じて、**必ず以下の【分岐 A】または【分岐 B】のいずれか一方のみ**を実行してください。

### 【分岐 A: 改善点・不要コードが 1 点でも見つかった場合】
1. 見つかった改善点の中から**【もっとも重要な 1 点のみ】**を選択してください。
2. 対象のコードおよびドキュメントを修正・削除し、ADK 2.0 公式公開APIへ一本化してください。
3. ターミナルで `pytest` を実行し、全テストが合格することを確認してください。
4. 変更内容をステージングし、明確なコミットメッセージで `git commit` を実行してください。
   （例: `git commit -m "refactor(adk): ○○を廃止し ADK 2.0 公式 △△ に一本化"`）
5. コミット完了を報告してセッションを終了してください。
   - **【厳禁事項】**: この分岐 A を実行した場合は、**絶対に `OPTIMIZATION_COMPLETE` を出力してはなりません**。
   - ※改修後のコードベースの健全性は、次の新しいクリーンなセッションが客観的に検証します。

### 【分岐 B: 改善点・車輪の再発明・旧仕様の残存が【1点も存在しない】場合】
1. コードの修正やコミットは**【絶対に一切行わない】**でください。
2. チェックリストの全領域（Code Execution, Skill Management, Evaluation, App Lifecycle, ドキュメント整合性）において、現行コードが ADK 2.0 ベストプラクティスに完全に準拠している理由を監査レポートとして提示してください。
3. そして、回答の**最終行にのみ**以下のシグナルを出力してセッションを終了してください：

```
OPTIMIZATION_COMPLETE
```
