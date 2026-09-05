# edd-agent-tools 開発ルール (エージェント指向システム制約 / SSOT)

本ドキュメントは、`edd-agent-tools` パッケージを利用してスキル開発・自律改善・評価検証を実装するAIエージェントが遵守すべき **「厳密な開発制約 (System Rules)」** の単一真実源（Single Source of Truth）です。

---

## 🌟 【必須行動規範】作業開始時の設計思想確認 (Mandatory Initial Orientation)
**すべての AI エージェントは、タスクに着手する前に必ず本プロジェクトの最新設計思想と規約を確認し、全体像を把握した上で作業を開始しなければなりません。**

* **MCP リソース経由の確認（推奨）**:
  FastMCP サーバー（`edd-agent-mcp`）が提供する以下のリソースを優先的に読み込んでください：
  - `edd://docs/design_philosophy` : 中核設計思想・Two-Tier アーキテクチャ・カスケード解決・Prerequisites 方針
  - `edd://rules/agents` : プラットフォーム不変契約および変更可能領域の定義
  - `edd://guidelines/progressive_disclosure` : リソース分離（scripts/references/assets/examples）規約
* **ローカルファイル経由の確認**:
  MCP が利用できない環境では、以下の SSOT ファイルを直接参照してください：
  - [`edd-agent-tools/src/edd_agent_tools/docs/design_philosophy.md`](file:///workspace/edd-agent-tools/src/edd_agent_tools/docs/design_philosophy.md)
  - [`edd-agent-tools/src/edd_agent_tools/AGENTS.md`](file:///workspace/edd-agent-tools/src/edd_agent_tools/AGENTS.md)

---

## 0. プロジェクトの目的と設計哲学 (Project Vision & Core Purpose)

### 🎯 プロジェクトの北極星 (North Star)
本プロジェクトの究極の目的は、**「AI エージェントが自らのスキル（手順書・ドメイン知識・決定論的スクリプト）を自律的にテスト・診断・修復・進化させる自己進化システム（Self-Evolving Agentic Ecosystem）」** を構築することです。

### ⚖️ 業界標準の疎結合モデル (Convention-over-Configuration & Zero-Dependency)
pytest, Ansible, dbt 等の業界標準エコシステムに倣い、**「汎用ランタイム＆テストハーネス（pip パッケージ）」と「規約駆動・ゼロ依存アセット（スキル資産）」の完全な疎結合分離**を採用します。

* **なぜパッケージとスキルを疎結合に分離するのか？（技術的根拠）**:
  1. **探索空間の極小化 (Search Space Localization)**:
     エージェントがバグを修正したり性能を改善する際、変更対象が `skills/<skill-name>/` 内に閉じていれば、迷走せず迅速・正確に修正を完了できます。
  2. **爆発半径の極小化 (Blast Radius Minimization)**:
     スキル内のスクリプトが自己改善の試行錯誤で一時的に壊れても、共通パッケージや他のスキルを巻き込んでシステム全体が停止するリスクをゼロにします（審判と選手の完全隔離）。
  3. **サンドボックス評価の容易性 (Safe Sandboxing & Rollback)**:
     スキルが単一ディレクトリで完結しているため、仮想環境（`LocalWorkspaceEnv`）に安全に複製して何度でもテスト・評価・ロールバックが可能です。
  4. **ポータビリティの保証 (Drop-in Portability)**:
     スキルが外部パッケージに直接 Python import 依存しないことで、Claude Code, Antigravity, Cursor, Google ADK 等のあらゆる環境へ zip 1つで即座に配布・利用できます。

---

## 1. パッケージとスキルの責務分離 (Two-Tier Architecture & Separation of Concerns)

### A. 不変プラットフォーム層（pip ライブラリ: `edd-agent-tools`）の責務
全スキル共通の「変更不可な不変の評価・実行・検証プラットフォーム（汎用ランタイム＆テストハーネス）」に徹してください：
- **共通ドメインエンティティ (`core`)**: `SkillPackage`（`load_resource`, `execute_script` 自己完結実行カプセル化、エイリアス `Skill` 完備）, `SkillTests`
- **状態・レジストリ管理 (`state`)**: `SkillsState`（Tier 1〜3 管理, 依存 DAG 解析, `entry_points` 探索）
- **汎用静的リンター (`validation`)**: `SkillValidator`（AST/構文/実在検証、Prerequisites照合、白書命名規則、MCP再発明検知）
- **組み込みテンプレート & スキャフォールド & ZIP化 (`packaging`)**: `SkillScaffolder`, `SkillPackager`, `templates/*.md`（ADK公式 EvalSet および test_config.json インバージョン自動生成）
- **仮想環境サンドボックス & 多層評価・Tier昇格 (`evaluation`)**: `ContractTestRunner` ($pass^k$), `SimulationEvalRunner` (ADK純正 `TrajectoryEvaluator`: EXACT / IN_ORDER / ANY_ORDER), `AdkEvalAdapter` (LLM-as-a-Judge & Position Swapping & ADK純正 `RubricBasedFinalResponseQualityV1Evaluator` / `AgentEvaluator` / `TrajectoryEvaluator` / 型安全な専用 `ToolTrajectoryCriterion` / `RubricsBasedCriterion` / `EvalConfig` 直接連携), `CascadeTestRunner`, `LocalWorkspaceEnv`, `SkillDiagnoser`, `SkillOptimizer`
- **Google ADK 2.0 / MCP アダプタ (`adk` / `mcp`)**: `create_adk_skill_toolset`, `SkillToolset` (および `EddSkillToolset`: SkillsState / Tier 統合 Toolset: 3-Tier Progressive Disclosure: Tier適合ローカルスキルの全登録・L1 Frontmatter常時提示・L2 手順書/L3 スクリプトのオンデマンド開示、`enable_registry_search=False` によるローカル完結エージェントの検索ツール露出抑制・オーバーサーチ防止、動的探索用の `EddSkillRegistry` 併用、ADK公式 `UnsafeLocalCodeExecutor` 等の `BaseCodeExecutor` 標準注入・決定論的スクリプト実行), `EddSkillRegistry`, `create_mcp_server`
- **統合 CLI (`cli`)**: `edd`（`run`, `init`, `validate`, `package`, `eval` [--coverage, --live, --cli], `adk-eval` [--config, --cli], `tier-gate`, `diagnose`, `optimize`, `list`）

※ **自己完結性と公式準拠の保証**: 他プロジェクトに `pip install` された環境でも単独で完全動作するよう、パッケージ内部は外部プロジェクト固有パスへの暗黙依存を持たない完全自己完結設計とします。アドホックな車輪の再発明やプライベート属性（`_tools` 等）への裏口アクセス、独自の手動キーワード照合による偽ルーブリック判定、自前 `subprocess.run` 実行コードの再実装を完全排除し、ADK 公式コンポーネント（`BaseCodeExecutor`, `UnsafeLocalCodeExecutor`, `_SkillScriptCodeExecutor`, `await toolset.get_tools()`, `TrajectoryEvaluator`, `EvalSet`, `EvalConfig` [test_config.json: IN_ORDER & Rubrics], `RubricBasedFinalResponseQualityV1Evaluator`, `AgentEvaluator`）を直接使用します。Tool Trajectory 検証およびスクリプト実行は、ADK 2.0 純正の `run_skill_script`（args: `skill_name`, `file_path`, `args`, `positional_args`）および `RunSkillScriptTool` / `_SkillScriptCodeExecutor` に完全一本化し、ドメイン層での展開コード再実装やエージェントプロンプト内でのスキル名ハードコードを徹底排除します。トップレベルエージェント（`src/agent.py`）には公式推奨に従い `code_executor` を直接注入し、エージェントのライフサイクル制御には ADK 2.0 推奨の Callbacks（`before_agent_callback`, `after_agent_callback`）を活用します。


### B. 自己改善スキル資産層（`src/skills/`）の責務と依存関係ポリシー
- **個別ロジックのカプセル化**:
  スキルの業務ロジック、個別処理スクリプト（`scripts/`）、ドメインスキーマ（`references/`）、出力用テンプレート（`assets/`）、個別契約テスト（`tests/`）は、**必ずスキルディレクトリ内に隔離して実装**してください。
- **依存関係ポリシー (Dependency & Prerequisites Policy)**:
  1. **メタスキル (`skill-creator`, `skill-evolver`)**:
     - `pytest` が `pytest` のインストールを前提とするのと同様、**`pip install edd-agent-tools` を前提とし、統合 CLI `edd` を直接呼び出す手順書（CLI-as-an-API）** です。
     - 不要な薄型ラッパースクリプトを排除し、単一真実源（SSOT）と保守性を最大化します。
  2. **一般ドメインスキル（業務・ツールスキル）**:
     - 軽量ユーティリティ（例: `case-converter`, `secret-sanitizer`）は Python 標準ライブラリのみで完結させます。
     - 外部ライブラリ依存（例: `docx`, `xlsx`, `playwright` 等）が必要なスキルは、Anthropic 公式標準に従い `SKILL.md` の `## Requirements & Prerequisites` に必要な pip パッケージを明記します（環境構築されている前提で実行）。`SkillValidator` が AST 解析により記述漏れを自動検知します。
  3. **Don't reinvent MCP as scripts (MCP再発明の禁止)**:
     - 白書 Appendix A 準拠。外部API（GitHub, Slack, Salesforce等）との接続や外部データ取得は MCP ツールに委譲し、スキルスクリプト内で巨大な HTTP クライアントを再発明してはなりません。スキルは Know-how（決定論的手順と処理）に集中します。
  4. **白書標準 EDD (Evaluation-Driven Development) インバージョン開発と単一真実源 (SSOT)**:
     - 新規スキルの執筆時は、`SKILL.md` を書く前にまず `tests/{skill_name}.test.json`（単一真実源: SSOT）として **3つの正例 ＋ 3つの負例（計6ケース、白書 Page 22 必須要件）** の Google ADK 2.0 公式 `EvalSet`（`eval_set_id`, `eval_cases`, `conversation`, `Invocation`, `intermediate_data.tool_uses`, `rubrics`）を確定し、ツールの呼び出し軌跡と採点基準を先行定義します。ツール呼び出しは Google ADK 2.0 純正の **`run_skill_script`**（args: `skill_name`, `file_path`, `args`, `positional_args`）を第1級の標準（Primary Standard）として記述します。
     - **Google ADK 2.0 公式 `test_config.json`（`EvalConfig`）の標準配備**:
       `adk eval` CLI および `AgentEvaluator` の自動探索に適合するため、テストディレクトリには `test_config.json` を配備します。Progressive Disclosure（`list_skills` ➔ `load_skill` ➔ `run_skill_script`）を採用するエージェントを公平に評価するため、`tool_trajectory_avg_score` には `match_type: "IN_ORDER"` を標準指定し、`rubric_based_final_response_quality_v1`（LLM-as-a-Judge 評価）にベースルーブリックと判定モデル（`gemini-2.5-flash`）を設定します。
     - **責務分離の原則 (Responsibility Separation)**: ツール呼び出し・引数（`positional_args` / `args`）の検証は `expected_tool_calls` / `intermediate_data.tool_uses`（Trajectory レイヤー）に集約し、`rubric` は最終出力品質（正確性・簡潔性・会話フィラーの排除・負例時の適切な振る舞い）に特化させます。
     - 独自スキーマによるデータ二重管理を排し、Google ADK 公式 CLI `adk eval` や `AgentEvaluator` とそのまま直結動作します。
  5. **白書 Appendix A minimal SKILL.md 6大必須セクション構造**:
     - すべての `SKILL.md` は、`## When to use`, `## When NOT to use`, `## Workflow`, `## Examples`, `## Output format`, `## Anti-patterns to avoid` の 6 つの必須セクションで構成します。
  6. **Python import 境界の厳守**:
     - スキル内のスクリプトは外部パッケージ `edd_agent_tools` を直接 Python import してはなりません。CLI/IO 規約（`--help`、引数、標準入出力）またはサブプロセスでのみ疎結合に連携します。
- **二重 LLM 呼び出しの禁止**:
  スキル内のスクリプト内部で直接 LLM API を叩くバッチ処理を作らず、エージェント自身が `SKILL.md` の指示に従って対話・推論を行う設計としてください。

---

## 2. 自己進化のための変更境界ルール (Mutation Boundary Rules)
エージェントが自律的にスキルを進化・修復する際の境界線：

* **🟢 エージェント変更可能領域 (Mutable Zone: 自己進化対象)**:
  - `SKILL.md` (プロンプト指示、意思決定ツリー、トリガー条件、When NOT to use)
  - `scripts/` 配下の個別ドメインロジック（ビジネスルール・変換関数）
  - `references/` (ドメイン知識、スキーマ仕様)
  - `assets/` (出力用テンプレート・素材)
  - `examples/` (具象コード例・パターン集)
  - `tests/` (Google ADK 2.0 公式 EvalSet 評価データセット `*.test.json`)
* **🔴 エージェント不変・契約領域 (Immutable API Contract: 不変プラットフォーム)**:
  - `edd_agent_tools.*` (パッケージ内部のコード)
  - テスト評価ランナー・静的検証エンジン・Tier 昇格判定エンジン

---

## 3. 単一真実源の原則と Progressive Disclosure 規約 (Markdown-First)
* **単一真実源 (SSOT) ➔ `SKILL.md` & `*.test.json`**:
  スキルの仕様、トリガー条件、意思決定ツリー、ステップ手順はすべて `SKILL.md`（YAML Frontmatter + Markdown）に一元化し、評価基準は `tests/{skill_name}.test.json` に一元化する。
* **リソース分離**:
  - `scripts/`: 直接実行可能な決定論的スクリプト（Python標準 `snake_case`、CLI対応, `--help` 必須, Black-box 実行）
  - `references/`: ドメイン知識・スキーマ・仕様書（オンデマンド参照用）
  - `assets/`: 成果物にコピー・流用するためのテンプレート・素材
  - `examples/`: 具象コード例・パターン集（エージェントが真似できる実装例）
  - `tests/`: Google ADK 2.0 公式 EvalSet 評価データセット（単一真実源: SSOT）

* **実践的ワークフロー規約**:
  - **Reconnaissance-then-Action**: 変更前にデータ構造・セレクタをサンプリング調査する。
  - **Minimal Edits & Batching**: ピンポイントな最小編集とバッチ処理による非破壊編集を行う。
* **ボイラープレートの排除**:
  多層ラッパー構造（`models.py`, `handler.py`, `nodes/`）を作成せず、フラットで簡潔な実装を行う。

---

## 4. 型仕様とドメインモデルの厳密遵守
スキル操作・構文解析・テスト実行を行う新規機能やスクリプトを開発する際は、必ずパッケージ内に定義されたドメインモデルおよび評価ランナーに適合させてください。

* **スキル管理モデル**: `edd_agent_tools.SkillPackage` (エイリアス `Skill`), `edd_agent_tools.models.SkillSpec`, `edd_agent_tools.SkillsState`, `edd_agent_tools.models.SkillTier`
* **品質保証・パッケージング**: `edd_agent_tools.SkillValidator`, `edd_agent_tools.SkillScaffolder`, `edd_agent_tools.SkillPackager`
* **評価実行基盤**: `edd_agent_tools.ContractTestRunner`, `edd_agent_tools.SimulationEvalRunner`, `edd_agent_tools.CascadeTestRunner`, `edd_agent_tools.SkillDiagnoser`, `edd_agent_tools.SkillOptimizer`
* **Google ADK 統合**: `edd_agent_tools.adk.create_adk_skill_toolset`, `edd_agent_tools.adk.SkillToolset`, `edd_agent_tools.adk.EddSkillToolset`, `edd_agent_tools.adk.EddSkillRegistry`

---

## 5. 依存性注入 (Dependency Injection) 制約
テスト実行や安全な試行錯誤を行うスクリプトは、自身の内部で OS や実ファイルシステムに直接アクセスしてはなりません。

* **実行環境の操作制限**:
  必ず引数として注入される `env: WorkspaceEnvProtocol`（`LocalWorkspaceEnv` 等の仮想環境）のみを介して、ファイルの書き込み、表示、テスト実行を行ってください。
* **目的**: テスト実行中の環境破壊や副作用を完全に排除し、安全に何度でもテストを再実行可能にするため。

---

## 6. 自動生成物に対する品質ハーネス (Quality Gates)
スキルの新規生成や改修時は、必ず以下の4段階品質保証パイプラインを遵守する：
1. **Stage 1 (Logical Extraction)**: パッケージ同梱テンプレートまたは `assets/templates/` を活用した論理設計・雛形生成（`edd init`）
2. **Stage 2 (Static Linter)**: `SkillValidator`（`edd validate`）による静的リンター（構文・実在整合性・Prerequisites外部依存・文字数制約）の 100% 合格
3. **Stage 3 (Contract & Trigger Verification)**: `ContractTestRunner` / `SimulationEvalRunner`（`edd eval`）による契約テスト 100% & トリガーテスト 90% 合格
4. **Stage 4 (Self-Healing & Tier Promotion)**: テスト失敗時の `edd diagnose` ➔ 差分修正 ➔ `edd tier-gate` による Tier 1〜3 昇格判定

---

## 7. プロンプトおよび仕様書の文体規約 (Imperative Form & Routing Algorithm)
* **動詞起点・客観的指示 (Imperative Instructions)**:
  `SKILL.md` および指示プロンプトはすべて客観的な指示（"To accomplish X, do Y" / "Xを実行するには、Yを行う" 形式）で記述し、会話調や曖昧な助動詞（you should, please）を排除してください。
* **Frontmatter の description (Routing Algorithm)**:
  `description` はエージェントがスキルを発動するかを判断する唯一のルーティング指標です。以下の3要素を 50〜100 words (≤1024 chars) で構成してください：
  1. **動詞起点（Verb-led sentence）**: 何を行うスキルかを端的に定義（例: "Converts text between case styles..."）
  2. **Use when ...**: トリガー条件・発話キーワード
  3. **Do NOT use for ...**: 誤爆を防ぐ除外条件・境界定義
* **Context Rot & Context Debt 対策**:
  - `SKILL.md` 本文は 5,000 words 以内に抑え、詳細な仕様やエッジケースは `references/` に分離（Progressive Disclosure）。
  - 「Give the reason, not just the rule」: `ALWAYS` や `NEVER` などの大文字命令を乱用せず、設計理由と客観的指示を記述する。
  - **Shift Intelligence Left**: 決定論的な処理は `scripts/` にオフロードし、CLI `--help` によるブラックボックス実行を行う。

---

## 8. スキル命名規則と ADK 2.0 完全一致要件 (Naming Conventions)
* **Directory Name & Skill Name (Frontmatter)**: **`kebab-case` で完全一致させる（例: `case-converter`）**
  - **重要**: Google ADK 2.0 公式ランタイム（`load_skill_from_dir`）は、内部で `skill_dir.name == frontmatter.name`（完全一致）をアサートしており、不一致の場合例外（`ValueError`）を送出します。そのため、ディレクトリ名とスキル名は必ず一致させて配置します。
  - なお、白書 Appendix A で言及される `snake_case` ディレクトリ名（例: `case_converter`）が万一指定された場合でも、`edd` ランタイム（`SkillsState`, `cli`）は双方向で透過的に自動解決します。
* **Script Name**: **`snake_case`（例: `case_converter.py`）** - Python モジュール標準。
* **動名詞の推奨 (Prefer gerund form)**: 名詞（`pdf-processor`）より動名詞（`processing-pdfs`）を推奨。
* **ベンダー名・汎用名の排除**: `gemini-*`, `claude-*` や `utils`, `tools` などの曖昧な命名を禁止。

