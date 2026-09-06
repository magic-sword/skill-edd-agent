# Agent Skill レビュールーブリック (Review Rubrics)

本ドキュメントは、Google 『Agent Skills』ホワイトペーパー（May 2026）および Google ADK 2.0 に準拠したスキル品質監査のためのルーブリック（採点基準）です。
独立審査官（Critic / Reviewer）は、生成されたスキルのコード、SKILL.md、テストケースを以下の 4 つの観点から客観的に評価します。

---

## 1. 過学習・テストゲーミングの排除 (Anti-Overfitting & Generalization)
AI エージェントが評価メトリクスを満たすためにテストケースの入力値に過学習（Overfit）していないかを検査します。

* **🚨 不合格パターン (FAIL)**:
  - スクリプト内に `tests/*.test.json` の入力文字列やファイルパスと完全一致する `if text == "..."` や `if raw == pattern:` 等のハードコード分岐が存在する。
  - テストケース特有のフォーマット（特定のスペース数、特定の値）にのみ合わせた決め打ちのロジックが存在する。
* **✅ 合格基準 (PASS)**:
  - アルゴリズムが抽象化されており、未知の入力・任意の列数や文字幅に対しても一貫して動作する。
  - 設計が「入力のパース ➔ 内部表現（データモデル）変換 ➔ レンダリング」の多段パイプラインとして構造化されている。

---

## 2. 決定論的ツール化と責務分離 (Deterministic Tooling & Separation)
処理の複雑さに応じてロジックが適切に分離されているかを検査します。

* **🚨 不合格パターン (FAIL)**:
  - 複雑な文字列操作・表計算・正規表現処理を LLM のプロンプト（指示文）だけで処理させようとしている。
  - 巨大な外部 API クライアントを再発明している（MCP 再発明の禁止）。
* **✅ 合格基準 (PASS)**:
  - 決定論的処理（フォーマット、変換、サニタイズ等）はすべて `scripts/` 配下の Python スクリプトに集約されている（Shift Intelligence Left）。
  - スクリプトは `--help` に対応し、単体でサブプロセスから正常に呼び出し可能である。

---

## 3. 白書 Appendix A 品質基準 (Whitepaper Quality Bar)
`SKILL.md` の記述が白書の品質要件を満たしているかを検査します。

* **🚨 不合格パターン (FAIL)**:
  - `description` が "A helpful skill for..." や "Helps with..." などの曖昧な表現で始まっている。
  - `When NOT to use`（使ってはならないケース）が欠落しており、境界が曖昧。
  - `{task}`, `{skill_name}`, `<TODO>` 等のプレースホルダーが残存している。
  - 大文字の禁止命令（"ALWAYS", "NEVER"）が乱用され、設計理由（Rationale）が書かれていない。
* **✅ 合格基準 (PASS)**:
  - `description` は動詞起点（"Format...", "Convert...", "Sanitize..."）で、トリガーキーワードが前置されている。
  - 白書 6 大必須セクション（`When to use`, `When NOT to use`, `Workflow`, `Examples`, `Output format`, `Anti-patterns to avoid`）がすべて具体的かつ実例付きで記載されている。
  - 5,000 ワード未満に抑えられ、詳細仕様は `references/` に分離されている（Progressive Disclosure）。

---

## 4. 堅牢性とエラーハンドリング (Robustness & Error Handling)
異常系入力やエッジケースに対するスクリプトの堅牢性を検査します。

* **🚨 不合格パターン (FAIL)**:
  - 空文字、空行のみ、不正な構文が入力された際に例外（IndexError, KeyError 等）で未捕捉クラッシュする。
  - ユーザーのファイルをバックアップなしに破壊的に上書きする。
* **✅ 合格基準 (PASS)**:
  - 空入力や不正なフォーマットに対して、分かりやすいエラーメッセージを出力し、適切な終了コード（0 または 1）で安全に終了する。
