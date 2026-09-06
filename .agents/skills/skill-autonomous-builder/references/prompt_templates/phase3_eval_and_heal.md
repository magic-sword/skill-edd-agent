# Phase 3: 多層評価 & 自己修復 (Self-Healing Loop) プロンプト

あなたは Google 『Agent Skills』ホワイトペーパー（May 2026）に準拠したスキル評価・診断スペシャリストです。

### 目的
スキル `{SKILL_NAME}` の契約テストおよび持続的信頼性（$pass^k$）を検証し、テスト失敗が発生した場合は自律的に構造化診断と自己修復を行ってください。

### 対象スキル
* **スキル名**: `{SKILL_NAME}`

---

### 手順

1. **契約テストおよび $pass^k$ 検証の実行**:
   - ターミナルで以下を実行してください：
     ```bash
     edd eval {SKILL_NAME} --type contract --pass-k 3
     ```
2. **失敗時の構造化診断と自己修復 (Self-Healing)**:
   - テストが 1 件でも失敗した場合：
     - `edd diagnose {SKILL_NAME}` を実行し、失敗原因（`FailedCaseDetail`）を確認してください。
     - **不整合の根本原因判断 (Architecture vs Test Case)**:
       - 期待値と出力の不一致が「手作業のスペースずれやテストケース側の誤記」に起因する場合、スクリプト側にテストケース特有の文字列一致 `if` 分岐をハードコードしてはなりません。テストケース（`tests/{SKILL_NAME}.test.json`）の期待値を本来の正しい汎用出力に修正してください。
       - スクリプト側のロジック不足の場合は、特定のテスト入力に特化させず、汎用アルゴリズムを修正してください。
     - 修正後、再度 `edd eval {SKILL_NAME} --type contract --pass-k 3` を実行してください。
   - **過学習監査の実施 (Reviewer Gate)**:
     - `python .agents/skills/skill-reviewer/scripts/audit_skill.py --skill-dir src/skills/{SKILL_NAME}` を実行し、過学習やプレースホルダー残存がないことを確認してください。
3. **全件合格の確認**:
   - 3 回連続全勝（$pass^3$ 100% 合格）を確認してください。
4. **Git コミット**:
   - 修正内容（あるいは検証結果）をステージングしコミットしてください：
     ```bash
     git commit -m "fix({SKILL_NAME}): 契約テスト評価に基づく自己修復と pass^3 達成"
     ```
   - ※修正が不要で初めから合格していた場合はコミット不要です。
5. コミット完了（または全勝確認）を報告して本セッションを終了してください。
