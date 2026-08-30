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

---

## 1. パッケージとスキルの責務分離 (Two-Tier Architecture & Self-Evolution Isolation)

### A. 不変プラットフォーム層（pip ライブラリ: `edd-agent-tools`）の責務
全スキル共通の「変更不可な不変の評価・実行・検証プラットフォーム」に徹してください：
- **仮想環境サンドボックス**: `LocalWorkspaceEnv`, `SubprocessSandbox`
- **多層評価・Tier昇格エンジン**: `ContractTestRunner`, `SimulationEvalRunner`, `CascadeTestRunner`
- **汎用静的リンター**: `SkillValidator`（AST/構文/実在検証）
- **状態・レジストリ管理**: `SkillsState`（Tier 1〜3 管理, 依存 DAG 解析）
- **配布用 ZIP パッケージャ**: `package_skill_cli`
- **Google ADK 2.0 / MCP アダプタ**: `create_adk_skill_toolset`, `EddSkillToolset`
- **統合 CLI**: `edd`（`run`, `init`, `validate`, `package`, `eval`, `tier-gate`, `diagnose`, `optimize`, `list`）

※ **過度なテンプレート・プロンプトハードコードの禁止**:
Markdown の文体やテンプレート生成ロジックを pip パッケージ側に過度にハードコードしてはなりません。エージェントがプロンプトを進化させるときに pip パッケージのコードを変更する必要をなくすためです。

### B. 自己改善スキル資産層（`src/skills/`）の責務
- **個別ロジックのカプセル化**:
  スキルの業務ロジック、個別処理スクリプト（`scripts/`）、ドメインスキーマ（`references/`）、出力用テンプレート（`assets/`）、個別契約テスト（`tests/`）は、**必ずスキルディレクトリ内に隔離して実装**してください。
- **テンプレート素材の単一真実源 (SSOT)**:
  スキル作成用の Markdown テンプレート（`workflow_template.md`, `task_based_template.md`, `reference_template.md`, `capabilities_template.md`）は `src/skills/skill-creator/assets/templates/` を真実源とし、エージェントの推論と自己改善によって進化させます。
- **完全な自己完結性（Portability / Zero-dependency）**:
  スキル内のスクリプトは外部パッケージ `edd_agent_tools` を直接 Python import してはなりません。Python 標準ライブラリのみで実装するか、統合 CLI `edd` を subprocess 呼び出しする設計としてください。
- **二重 LLM 呼び出しの禁止**:
  スキル内のスクリプト内部で直接 LLM API を叩くバッチ処理を作らず、エージェント自身が `SKILL.md` の指示に従って対話・推論を行う設計としてください。

---

## 2. 単一真実源の原則と Progressive Disclosure 規約 (Markdown-First)
* **単一真実源 (SSOT) ➔ `SKILL.md`**:
  スキルの仕様、トリガー条件、意思決定ツリー、ステップ手順はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化する。
* **3層リソース分離**:
  - `scripts/`: 直接実行可能な決定論的スクリプト（CLI対応, `--help` 必須）
  - `references/`: ドメイン知識・スキーマ・仕様書（オンデマンド参照用）
  - `assets/`: 成果物にコピー・流用するためのテンプレート・素材
  - `tests/`: 契約テストおよびシミュレーション評価ケース（`*.evalset.json`）
* **ボイラープレートの排除**:
  多層ラッパー構造（`models.py`, `handler.py`, `nodes/`）を作成せず、フラットで簡潔な実装を行う。

---

## 3. 型仕様とドメインモデルの厳密遵守
スキル操作・構文解析・テスト実行を行う新規機能やスクリプトを開発する際は、必ずパッケージ内に定義されたドメインモデルおよび評価ランナーに適合させてください。

* **スキル管理モデル**: `edd_agent_tools.Skill`, `edd_agent_tools.models.SkillSpec`, `edd_agent_tools.SkillsState`, `edd_agent_tools.models.SkillTier`
* **品質保証モデル**: `edd_agent_tools.models.SkillLogicDraft`, `edd_agent_tools.SkillValidator`
* **評価実行基盤**: `edd_agent_tools.ContractTestRunner`, `edd_agent_tools.SimulationEvalRunner`, `edd_agent_tools.CascadeTestRunner`, `edd_agent_tools.SkillDiagnoser`, `edd_agent_tools.SkillOptimizer`
* **Google ADK 統合**: `edd_agent_tools.adk.create_adk_skill_toolset`, `edd_agent_tools.adk.EddSkillToolset`

---

## 4. 依存性注入 (Dependency Injection) 制約
テスト実行や安全な試行錯誤を行うスクリプトは、自身の内部で OS や実ファイルシステムに直接アクセスしてはなりません。

* **実行環境の操作制限**:
  必ず引数として注入される `env: WorkspaceEnvProtocol`（`LocalWorkspaceEnv` 等の仮想環境）のみを介して、ファイルの書き込み、表示、テスト実行を行ってください。
* **目的**: テスト実行中の環境破壊や副作用を完全に排除し、安全に何度でもテストを再実行可能にするため。

---

## 5. 自動生成物に対する品質ハーネス (Quality Gates)
スキルの新規生成や改修時は、必ず以下の4段階品質保証パイプラインを遵守する：
1. **Stage 1 (Logical Extraction)**: `assets/templates/` を活用した論理設計・雛形生成（`init_skill.py`）
2. **Stage 2 (Static Linter)**: `SkillValidator`（または `quick_validate.py`）による静的リンター（構文・実在整合性・文字数制約）の 100% 合格
3. **Stage 3 (Contract & Trigger Verification)**: `ContractTestRunner` / `SimulationEvalRunner` による契約テスト 100% & トリガーテスト 90% 合格
4. **Stage 4 (Self-Healing & Tier Promotion)**: テスト失敗時の `edd diagnose` ➔ 差分修正 ➔ `edd tier-gate` による Tier 1〜3 昇格判定

---

## 6. プロンプトおよび仕様書の文体規約 (Imperative Form)
* **動詞起点・客観的指示**: SKILL.md および指示プロンプトはすべて客観的な指示（"To accomplish X, do Y" / "Xを実行するには、Yを行う" 形式）で記述し、会話調や曖昧な助動詞を排除してください。
* **Frontmatter の description**: 第三者視点（"This skill should be used when..."）で、トリガー条件・対象ファイル・対応タスクを100 words以内で極めて具体的に記述してください。
