# スキル設計・開発ガイドライン (Skill Design Guide)

Anthropic 公式標準（Markdown-First & Progressive Disclosure）および Google ADK 2.0 に準拠したスキル設計・開発の標準作業手順（SOP）。

---

## 1. 単一真実源の原則 (Single Source of Truth)
* スキルの仕様定義はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化し、自然言語とコードのシームレスな統合を図る。

---

## 2. 3層リソース分離と Progressive Disclosure (Google ADK 2.0 純正規格)
* **`scripts/` (実行用スクリプト / 決定論的ブラックボックスツール - Level 3)**:
  - 決定論的処理、ファイル変換、APIリクエストなどを直接実行可能なスクリプト（Python / Bash）として配置する。
  - すべてのスクリプトは `argparse`（`--help` サポート）を備えた直接実行可能な CLI ツールとして実装する。
  - **Black-box Execution 規約**: エージェントはまず `--help` で引数仕様を確認し、コンテキスト節約のためスクリプト本体のソースコードを不必要にコンテキストへ読み込まない。
  - **二重 LLM 呼び出しの禁止**: スクリプト内部で LLM API を直接叩かず、推論はエージェント自身が行う。
  - `models.py` や `handler.py` 等の多層ラッパー構造を作らず、単一のフラットで簡潔な実装とする。
* **`references/` (参照用ドキュメント / オンデマンド知識 - Level 3)**:
  - API仕様、データベーススキーマ、ガイドライン、ルールブック、および使用例・パターン集（`example_usage.py` や `guide.md`）を配置する。
  - 長大な詳細情報は `SKILL.md` に直接書かず、ここに分離してLLMが必要時にオンデマンドで読むようにする。
* **`assets/` (出力用テンプレート・素材 - Level 3)**:
  - 成果物にコピー・流用するためのボイラープレート、HTML/Reactプロジェクト雛形、設定ファイルテンプレート、サンプルデータを配置する。
* **不要ディレクトリの排除 (Clean Directory)**:
  - リソースが存在しない空の `assets/`, `references/` ディレクトリは作成せず、不要なノイズを完全に排除する。Google ADK 2.0 では独自 `examples/` ディレクトリは設けず、用例は `references/`、`assets/`、または `SKILL.md` の `## Examples` セクションに集約する。

---

## 3. Frontmatter & メタデータ規約 (Level 1 - Routing Algorithm)
* **`name`**: ハイフンケース（ケバブケース: `^[a-z0-9]+(-[a-z0-9]+)*$`）のみ（例: `pdf-tools`, `git-conflict-resolver`）。
* **`description`**: エージェントがスキルを発動するかを判断する**ルーティングアルゴリズム**として設計する。以下の3要素を 50〜100 words (≤1024 chars) で構成する：
  1. **動詞起点（Verb-led sentence）**: 何を行うスキルかを端的に定義（例: "Converts text between case styles..."）
  2. **Use when ...**: トリガー条件・発話キーワード
  3. **Do NOT use for ...**: 誤爆を防ぐ除外条件・境界定義
* **`pattern`**: 4大スキルパターン（`workflow`, `task_based`, `reference`, `capabilities`）のいずれかを指定。

---

## 4. 4大スキルパターンの選定基準
1. **`workflow` (ワークフロー型)**:
   - 順序立てられたステップや、条件別の分岐（Decision Tree）が存在する作業。
2. **`task_based` (タスク集型)**:
   - 独立した複数の操作・スクリプト群を提供するツール集。
3. **`reference` (ガイドライン型)**:
   - 規約、設計標準、ドメイン知識の提供が主目的のスキル。
4. **`capabilities` (統合機能型)**:
   - 複合的なシステム連携・包括的機能を提供するスキル。

---

## 5. 既存インベントリ照合と重複排除 (Inventory Alignment)
* 新規スキルの作成を検討する際、まず既存スキルのインベントリ（`SkillsState.list_skills()`）を照合する。
* 既存スキルでカバー可能な要件、または既存スキルの拡張で対応可能な場合は、重複した別スキルを作らず既存スキルの更新（Update）を優先する。

---

## 6. プロンプトおよび仕様書の文体規約 (Imperative Form - Level 2)
* すべての指示は動詞起点（"To accomplish X, do Y" / "Xを実行するには、Yを行う" 形式）で客観的に記述する。
* 「〜してください」「〜する必要があります」等の曖昧・冗長な会話表現は排除する。

---

## 7. 実践的ワークフロー・パターン
* **Reconnaissance-then-Action（偵察先行型）パターン**:
  - ファイルやDOMを変更する前に、まず対象の構造、スキーマ、セレクタ、AST、メタデータをサンプリング・調査（Reconnaissance）し、仕様を確定させてから本編集を実行する。
* **Minimal Edits & Batching（最小編集とバッチ処理）原則**:
  - ドキュメントやコードの修正は、変更対象のみをピンポイントで編集し、無関係な行やメタデータを破壊しない（全置換を避ける）。
  - 多数の変更がある場合は 3〜10 個単位のバッチに分割して段階的に適用・検証する。

---

## 8. 4次元ネガティブ・フレームワーク (When NOT to Use 導出基準)
エージェントの過剰適用（Over-tooling）や競合による誤発火を防ぐため、以下の4軸から必ず客観的な非適用条件を導出して `SKILL.md` に明記する：
1. **粒度境界 (Granularity)**: 単発のワンライナーや標準OSコマンドで完結する軽微なタスクにはスキルを起動しない。
2. **技術的限界 (Out-of-Scope)**: 似ているがドメイン範囲外の別処理（例: 単純ケース変換スキルでの言語AST構文解析や自然言語翻訳）。
3. **ライフサイクル分離 (Lifecycle)**: 前後のフェーズ（作成、診断、評価、最適化）を混同せず、各スキルの単一責任を維持する。
4. **インベントリ照合 (Inventory)**: 既存スキルで既にカバーされているタスクは重複作成せず、既存スキルの拡張として扱う。

---

## 9. スキル配布用パッケージングとマルチプラットフォーム対応 (Packaging & Portability)
* 完成したスキルは `edd validate <skill-path>` で静的バリデーションを実行し、`edd package <skill-path>` を用いて配布用 ZIP アーカイブとして出力する。
* 各スキルは Google ADK 2.0（`google.adk.skills.load_skill_from_dir`）、Claude Code、Antigravity、Cursor 等のあらゆる主要エージェント基盤へドロップイン可能であり、`Skill.adk_skill` プロパティを通じて ADK 純正の `Skill` / `SkillToolset` へシームレスにマウント可能。

---

## 10. 白書 Appendix A minimal SKILL.md 6大必須セクション標準
白書 Appendix A に準拠し、すべての `SKILL.md` は以下の 6 つの必須セクションを備える：
1. **`## When to use`**: 具体的なトリガー条件、発話キーワード、適用シナリオ。
2. **`## When NOT to use`**: 粒度境界・技術的限界・ライフサイクル分離・インベントリ照合に基づく明確な除外条件。
3. **`## Workflow`**: 決定論的ステップ手順と CLI 実行コマンド。
4. **`## Examples`**: 入力発話と期待出力の具体例（Few-shot ガイダンス）。
5. **`## Output format`**: 成果物仕様、ファイル配置、回答形式。
6. **`## Anti-patterns to avoid`**: コンテキスト浪費や破壊的変更を防ぐための注意事項。

