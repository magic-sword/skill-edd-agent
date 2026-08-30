# edd-agent-tools 開発ルール (エージェント指向システム制約 / SSOT)

本ドキュメントは、`edd-agent-tools` パッケージを利用してスキル開発・自律改善・評価検証を実装するAIエージェントが遵守すべき **「厳密な開発制約 (System Rules)」** の単一真実源（Single Source of Truth）です。

---

## 0. プロジェクトの目的と設計哲学 (Project Vision & Core Purpose)

### 🎯 プロジェクトの北極星 (North Star)
本プロジェクトの究極の目的は、**「AI エージェントが自らのスキル（手順書・ドメイン知識・決定論的スクリプト）を自律的にテスト・診断・修復・進化させる自己進化システム（Self-Evolving Agentic Ecosystem）」** を構築することです。

### ⚖️ 最重要トレードオフの原則 (The Core Trade-off)
一般的なソフトウェア開発では「DRY原則（重複排除・共通ライブラリ化）」が重視されますが、本プロジェクトでは **「自己改善の局所性（Locality of Mutation）と安全な隔離（Isolation）」を DRY原則よりも上位の原則** として優先します。

* **なぜパッケージに個別処理を集約してはならないのか？（技術的根拠）**:
  1. **探索空間の極小化 (Search Space Localization)**:
     エージェントがバグを修正したり性能を改善する際、変更対象が `skills/<skill-name>/` 内に閉じていれば、迷走せず迅速・正確に修正を完了できます。
  2. **爆発半径の極小化 (Blast Radius Minimization)**:
     スキル内のスクリプトが自己改善の試行錯誤で一時的に壊れても、共通パッケージや他のスキルを巻き込んでシステム全体が停止するリスクをゼロにします。
  3. **サンドボックス評価の容易性 (Safe Sandboxing & Rollback)**:
     スキルが単一ディレクトリで完結しているため、仮想環境（`LocalWorkspaceEnv`）に安全に複製して何度でもテスト・評価・ロールバックが可能です。
  4. **ポータビリティの保証 (Drop-in Portability)**:
     スキルが外部パッケージに直接依存しないことで、Claude Code, Antigravity, Cursor, Google ADK 等のあらゆる環境へ zip 1つで即座に配布・利用できます。

## 1. パッケージとスキルの責務分離 (Two-Tier Architecture & Self-Evolution Isolation)

### A. スキル個別ロジックの完全隔離 (Self-Contained Skill Isolation)
* **個別処理のスキル内カプセル化**:
  スキルの業務ロジック、個別処理スクリプト（`scripts/`）、ドメインスキーマ（`references/`）、出力用テンプレート（`assets/`）、個別契約テスト（`tests/`）は、**必ずスキルディレクトリ内に隔離して実装**してください。
* **自己改善エージェント（Self-Evolution）のための探索境界**:
  エージェントがスキルを自律改善・修復する際、修正対象の探索空間（Search Space）を `skills/<skill-name>/` 内に局所化し、変更の爆発半径（Blast Radius）を極小化するためです。スキル固有のロジックが外部パッケージに流出すると、エージェントが修正箇所を特定できず自己改善ループが破綻します。

### B. アンチパターン：過度なパッケージ集約の禁止 (Anti-Pattern: Excessive Package Centralization)
* **DRY 原則の過剰適用によるパッケージ移転の禁止**:
  「似た処理があるから」「共通化できるから」という理由だけで、スキル固有の処理スクリプトを pip パッケージ（`edd-agent-tools`）内へ過度に移転・集約してはなりません。
* **パッケージ（pip ライブラリ: `edd-agent-tools`）の責務**:
  全スキル共通の「変更不可な不変の評価・実行・検証プラットフォーム」に徹してください：
  - サンドボックス仮想環境（`LocalWorkspaceEnv`）
  - 多層評価・Tier昇格エンジン（`ContractTestRunner`, `SimulationEvalRunner`, `CascadeTestRunner`）
  - 汎用静的バリデータ（`SkillValidator`）
  - スキルレジストリ・探索（`SkillsState`）
  - Google ADK 2.0 / MCP アダプタ（`EddSkillToolset`）
  - 統合 CLI（`edd run/init/validate/package/eval/tier-gate/diagnose/optimize`）

### C. スキル（`skills/`）の責務とポータビリティ:
* **完全な自己完結性（Portability / Zero-dependency）**:
  スキル内のスクリプトは外部パッケージ `edd_agent_tools` を直接 Python import してはなりません。Python 標準ライブラリのみで実装するか、統合 CLI `edd` を subprocess 呼び出しする設計としてください。
* **二重 LLM 呼び出しの禁止（Anti-pattern）**:
  スキル内のスクリプト内部で直接 LLM API を叩くバッチ処理を抱え込まず、エージェント自身が `SKILL.md` の指示に従って対話・推論を行う設計としてください。スクリプトは決定論的なブラックボックス CLI ツール（`argparse` / `--help` 対応）として実装してください。

---

## 2. 単一真実源の原則と Progressive Disclosure 規約 (Markdown-First)
*   **単一真実源 (SSOT) ➔ `SKILL.md`**:
    スキルの仕様、トリガー条件、意思決定ツリー、ステップ手順はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化する。
*   **3層リソース分離**:
    - `scripts/`: 直接実行可能な決定論的スクリプト（CLI対応）
    - `references/`: ドメイン知識・スキーマ・仕様書（オンデマンド参照用）
    - `assets/`: 成果物にコピー・流用するためのテンプレート・素材
*   **ボイラープレートの排除**:
    多層ラッパー構造（`models.py`, `handler.py`, `nodes/`）を作成せず、フラットで簡潔な実装を行う。

---

## 3. 型仕様とドメインモデルの厳密遵守 (What/How)
スキル操作・構文解析・テスト実行を行う新規機能やスクリプトを開発する際は、必ずパッケージ内に定義されたドメインモデルおよび評価ランナーに適合させてください。

*   **スキル管理モデル**: `edd_agent_tools.Skill`, `edd_agent_tools.models.SkillSpec`, `edd_agent_tools.SkillsState`, `edd_agent_tools.models.SkillTier`
*   **品質保証モデル**: `edd_agent_tools.models.SkillLogicDraft`, `edd_agent_tools.SkillValidator`
*   **自動生成エンジン**: `edd_agent_tools.SkillCreationEngine`, `edd_agent_tools.SkillTemplateEngine`
*   **評価実行基盤**: `edd_agent_tools.ContractTestRunner`, `edd_agent_tools.SimulationEvalRunner`, `edd_agent_tools.CascadeTestRunner`, `edd_agent_tools.SkillDiagnoser`, `edd_agent_tools.SkillOptimizer`

各クラスのシグネチャ、引数の名前、戻り値の型、発生すべき例外については、上記コード内の **Docstring および Type Hints** を唯一の真実のソースとして厳密に従ってください。

---

## 4. 依存性注入 (Dependency Injection) 制約 (What/How)
テスト実行や安全な試行錯誤を行うスクリプトは、自身の内部で OS や実ファイルシステムに直接アクセスしてはなりません。

*   **実行環境の操作制限**:
    必ず引数として注入される `env: WorkspaceEnvProtocol`（`LocalWorkspaceEnv` 等の仮想環境）のみを介して、ファイルの書き込み、表示、テスト実行を行ってください。
    *   ファイルの作成・書き込み ➔ `env.step(WriteFileAction(...))`
    *   ファイルの表示・確認 ➔ `env.step(ViewFileAction(...))`
    *   テストコマンド (pytest) の実行 ➔ `env.step(RunPytestAction())`
*   **目的**: テスト実行中の環境破壊や副作用を完全に排除し、安全に何度でもテストを再実行可能にするため。

---

## 5. 自動生成物に対する品質ハーネス (Quality Gates)
スキルの新規生成や改修時は、必ず以下の4段階品質保証パイプラインを遵守する：
1. **Stage 1 (Logical Extraction)**: `SkillLogicDraft` による論理設計抽出
2. **Stage 2 (Deterministic Rendering)**: `SkillTemplateEngine` による決定論的 SKILL.md レンダリング
3. **Stage 3 (Static Linter)**: `SkillValidator`（または `quick_validate.py`）による静的リンター（構文・実在整合性・文字数制約）の 100% 合格
4. **Stage 4 (Contract Verification)**: `ContractTestRunner` による初期契約テスト検証

---

## 6. プロンプトおよび仕様書の文体規約 (Imperative Form)
*   **動詞起点・客観的指示**: SKILL.md および指示プロンプトはすべて客観的な指示（"To accomplish X, do Y" / "Xを実行するには、Yを行う" 形式）で記述し、会話調や曖昧な助動詞（「〜してください」等）を排除してください。
*   **Frontmatter の description**: 第三者視点（"This skill should be used when..."）で、トリガー条件・対象ファイル・対応タスクを100 words以内で極めて具体的に記述してください。

---

## 7. ドキュメント化の設計思想と各ファイルの役割分担 (What/How)
*   **`README.md`**: パッケージ全体の主要機能、インストール方法、CLI/MCP 使用例のみを記述。
*   **`src/edd_agent_tools/AGENTS.md`**: AIエージェント向けシステム制約のみを記述（本ドキュメント）。
*   **`src/edd_agent_tools/docs/`**: 設計思想やアーキテクチャ背景を集中配置。
