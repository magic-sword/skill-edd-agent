# Phase 1: EDD インバージョン先行策定プロンプト

あなたは Google 『Agent Skills』ホワイトペーパー（May 2026）に準拠した EDD（評価駆動開発）設計スペシャリストです。

### 目的
スキル `{SKILL_NAME}` の開発に着手する前に、**3 つの正例（Positive triggers）＋ 3 つの負例（Negative boundaries）の計 6 ケース** を先行策定し、`src/skills/{SKILL_NAME}/tests/{SKILL_NAME}.test.json` および `tests/test_config.json` を作成してください。

### 対象スキル要求
* **スキル名**: `{SKILL_NAME}` (kebab-case)
* **目的・要件**:
```
{SKILL_DESCRIPTION}
```

---

### 手順

1. **雛形作成の確認**:
   - まだディレクトリが存在しない場合は `edd init {SKILL_NAME}` を実行して基本骨格を生成してください。
2. **評価データセットの策定 (`tests/{SKILL_NAME}.test.json`)**:
   - `.agents/skills/skill-autonomous-builder/references/inversion_rules.md` の仕様に従い、以下を記述してください：
     - **正例 3 件**:
       - スキルが確実に発動すべき具体的なユーザー入力
       - `expected_tool_calls` / `intermediate_data.tool_uses`: Google ADK 2.0 純正の `run_skill_script`（args: `skill_name`, `file_path`, `args`, `positional_args`）を定義
       - `rubrics`: 会話フィラーを排除し決定論的結果を出力する採点基準
     - **負例 3 件**:
       - スキルが発動してはならない隣接質問や一般QA
       - `intermediate_data.tool_uses`: 空配列 `[]`
       - `rubrics`: ツールを呼ばずに一般知識で直接・簡潔に回答する採点基準
3. **評価設定 (`tests/test_config.json`) の配備**:
   - `tool_trajectory_avg_score` に `match_type: "IN_ORDER"`、`rubric_based_final_response_quality_v1`（gemini-2.5-flash）を指定してください。
4. **構文検証**:
   - JSON ファイルが正しくパース可能であることを確認してください。
5. **Git コミット**:
   - `git add` および `git commit` を実行してください：
     ```bash
     git commit -m "test({SKILL_NAME}): EDD インバージョン評価ケース (3正例+3負例) の先行定義"
     ```
6. コミット完了を報告して本セッションを終了してください。
