# プロジェクト開発ルール (Workspace Entry Point)

本プロジェクトの究極の目的は、**「AI エージェントが自らのスキル（手順書・ドメイン知識・決定論的スクリプト）を自律的にテスト・診断・修復・進化させる自己進化システム（Self-Evolving Agentic Ecosystem）」** の構築です。
一般的な DRY 原則よりも **「エージェント自己改善の局所性（Locality）と安全な隔離（Isolation）」** を最上位の原則として優先します。

開発基盤パッケージ `edd-agent-tools` を**単一真実源（Single Source of Truth: SSOT）**として採用しています。

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

## 1. 業界標準の疎結合モデルと依存関係ポリシー (Runtime vs Content / Dependency Policy)
本プロジェクトは、pytest, Ansible, dbt 等の業界標準エコシステムと同様の **「汎用ランタイム＆テストハーネス（pipパッケージ） vs 規約駆動コンテンツ資産（スキル）」** 分離モデルを採用します。

* **汎用ランタイム＆テストハーネス (`edd-agent-tools` - pip パッケージ)**:
  - 状態管理・探索・DAG解析（`state`: `SkillsState`）
  - 共通ドメインエンティティ（`core`: `SkillPackage`, `SkillTests`）
  - 静的検証リンター（`validation`: `SkillValidator` - AST解析、Prerequisites照合、白書命名規則検査、MCP再発明検知）
  - パッケージ組み込み標準テンプレート & ZIP化（`packaging`: `SkillScaffolder`, `SkillPackager` - Snippet 3 インバージョン生成）
  - サンドボックス & 多層評価・Tier昇格（`evaluation`: `ContractTestRunner`, `SimulationEvalRunner`, `AdkEvalAdapter` [ADK純正 TrajectoryEvaluator, ResponseEvaluator ROUGE-1, RubricBasedFinalResponseQualityV1Evaluator, Position Swapping], `CascadeTestRunner`, `LocalWorkspaceEnv`）
  - Google ADK 2.0 / MCP アダプタ（`adk`: `create_adk_skill_toolset`, `EddSkillToolset` [UnsafeLocalCodeExecutor標準注入・重複コード実行排除], `EddSkillRegistry` / `mcp`: `create_mcp_server`）
  - 統合 CLI（`cli`: `edd run/init/validate/package/eval/tier-gate/diagnose/optimize`）
  ※ 他プロジェクトに `pip install` された環境でも単独で完全動作するよう、パッケージ内部は外部プロジェクト固有パスへの暗黙依存を持たない完全自己完結設計とします。公式 Code Executor を使用します。

* **規約駆動スキル資産層 (`src/skills/<skill>/`) と依存関係ポリシー**:
  1. **メタスキル (`skill-creator`, `skill-evolver`) の設計思想**:
     - `pytest` を実行するスクリプトが `pytest` のインストールを前提とするのと同様に、メタスキルは **`pip install edd-agent-tools` を前提とし、統合 CLI `edd` を直接呼び出す手順書（CLI-as-an-API）** です。
     - 不要な薄型ラッパースクリプトを排除し、単一真実源（SSOT）と保守性を最大化します。
  2. **一般ドメインスキル（業務・ツールスキル）の依存関係**:
     - **軽量ユーティリティ（例: `case-converter`, `secret-sanitizer`）**: Python 標準ライブラリのみで完結させ、追加セットアップ不要で即座に動作させます。
     - **外部ライブラリを必要とするスキル（例: `docx`, `xlsx`, `pdf`, `playwright` 等）**: Anthropic 公式標準に準拠し、`SKILL.md` 内の `## Requirements & Prerequisites` に必要な pip パッケージ（例: `python-docx`, `openpyxl` 等）を明記します。`SkillValidator` が AST 解析により記述漏れを自動検知します。
  3. **Don't reinvent MCP as scripts (MCP再発明の禁止)**:
     - 白書 Appendix A 準拠。外部API（GitHub, Slack, Salesforce等）との接続や外部データ取得は MCP ツールに委譲し、スキルスクリプト内で巨大な HTTP クライアントを再発明してはなりません。スキルは Know-how（決定論的手順と処理）に集中します。
  4. **白書標準 EDD (Evaluation-Driven Development) インバージョン開発と単一真実源 (SSOT)**:
     - 新規スキルの執筆時は、`SKILL.md` を書く前にまず `tests/{skill_name}_edd.evalset.json`（単一真実源: SSOT）として **3つの正例 ＋ 3つの負例（計6ケース、白書 Page 22 必須要件）** の Google ADK 2.0 公式 `EvalSet`（`eval_set_id`, `eval_cases`, `conversation`, `Invocation`, `intermediate_data.tool_uses`, `rubrics`）を確定し、ツールの呼び出し軌跡と採点基準を先行定義します。ツール呼び出しは Google ADK 2.0 純正の **`run_skill_script`**（args: `skill_name`, `file_path`, `args`, `positional_args`）を第1級の標準（Primary Standard）として記述します。
     - **Google ADK 2.0 公式 `test_config.json`（`EvalConfig`）の標準配備**:
       `adk eval` CLI および `AgentEvaluator` の自動探索に適合するため、テストディレクトリには `test_config.json` を配備します。Progressive Disclosure（`list_skills` ➔ `load_skill` ➔ `run_skill_script`）を採用するエージェントを公平に評価するため、`tool_trajectory_avg_score` には `match_type: "IN_ORDER"` を標準指定し、`rubric_based_final_response_quality_v1`（LLM-as-a-Judge 評価）にベースルーブリックと判定モデル（`gemini-2.5-flash`）を設定します。
     - **責務分離の原則 (Responsibility Separation)**: ツール呼び出し・引数の検証は `expected_tool_calls` / `intermediate_data.tool_uses`（Trajectory レイヤー）に集約し、`rubric` は最終出力品質（正確性・簡潔性・会話フィラーの排除・負例時の適切な振る舞い）に特化させます。
     - 独自スキーマによるデータ二重管理を排し、Google ADK 公式 CLI `adk eval` や `AgentEvaluator` とそのまま直結動作します。
  5. **白書 Appendix A minimal SKILL.md 6大必須セクション構造と ADK 公式仕様**:
     - すべての `SKILL.md` は、`## When to use`, `## When NOT to use`, `## Workflow`, `## Examples`, `## Output format`, `## Anti-patterns to avoid` の 6 つの必須セクションで構成します。Frontmatter の `allowed-tools` は ADK 2.0 純正仕様であるスペース区切り文字列として定義します。

  6. **Python import 境界の厳守**:
     - いずれのスキルもスクリプト内部から `import edd_agent_tools` などの直接 Python import は行わず、CLI/IO 規約（`--help`、引数、標準入出力、サブプロセス）のみで疎結合に連携します。
  7. **スキル命名規約と ADK 2.0 完全一致要件**:
     - Google ADK 2.0 公式ランタイム制約（`skill_dir.name == frontmatter.name`）に基づき、ディレクトリ名およびスキル名は `kebab-case`（例: `case-converter`）で完全一致させます。内部スクリプトは Python 標準の `snake_case`（例: `case_converter.py`）とします。

---

## 2. 自己進化のための変更境界ルール (Mutation Boundaries)
エージェントがスキルを進化・修復する際は、以下の境界線を厳格に遵守してください：

* **🟢 エージェント変更可能領域 (Mutable Zone: 自己進化対象)**:
  - `SKILL.md` (手順、プロンプト、意思決定ツリー、トリガー条件、When NOT to use)
  - `scripts/` 配下の個別ドメインロジック（ビジネスルール・変換関数）
  - `references/` (ドメイン知識、スキーマ仕様)
  - `assets/` (出力用テンプレート・素材)
  - `examples/` (具象コード例・パターン集)
  - `tests/` (白書 Snippet 3 形式評価データセット `*_edd.evalset.json`)

* **🔴 エージェント不変・契約領域 (Immutable API Contract: 不変プラットフォーム)**:
  - `edd-agent-tools` パッケージ内部のコード
  - 評価実行エンジン・静的検証エンジン・Tier 昇格判定エンジン

---

## 3. 単一真実源（SSOT）と開発規約の参照
* **エージェント開発制約の真実源**:
  エージェント向けの詳細開発制約、Progressive Disclosure、および4段階品質保証パイプラインはすべて [`edd-agent-tools/AGENTS.md`](file:///workspace/edd-agent-tools/src/edd_agent_tools/AGENTS.md) に定義されています。
* **MCP によるオンデマンド参照**:
  開発規約や設計ガイドラインは FastMCP サーバー（`edd-agent-mcp`）のリソース（`edd://rules/agents`, `edd://guidelines/*`, `edd://docs/*`）からも参照可能です。
* **ローカルインストール**:
  本パッケージは `pip install -e edd-agent-tools` でインストールして開発してください。