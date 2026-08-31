# プロジェクト開発ルール (Workspace Entry Point)

本プロジェクトの究極の目的は、**「AI エージェントが自らのスキル（手順書・ドメイン知識・決定論的スクリプト）を自律的にテスト・診断・修復・進化させる自己進化システム（Self-Evolving Agentic Ecosystem）」** の構築です。
一般的な DRY 原則よりも **「エージェント自己改善の局所性（Locality）と安全な隔離（Isolation）」** を最上位の原則として優先します。

開発基盤パッケージ `edd-agent-tools` を**単一真実源（Single Source of Truth: SSOT）**として採用しています。

---

## 1. 業界標準の疎結合モデル (Runtime vs Content / Zero-Dependency)
本プロジェクトは、pytest, Ansible, dbt 等の業界標準エコシステムと同様の **「汎用ランタイム＆テストハーネス（pipパッケージ） vs 規約駆動コンテンツ資産（スキル）」** 分離モデルを採用します。

* **汎用ランタイム＆テストハーネス (`edd-agent-tools` - pip パッケージ)**:
  - 状態管理・探索・DAG解析（`state`: `SkillsState`）
  - 静的検証リンター（`validation`: `SkillValidator`）
  - パッケージ組み込み標準テンプレート & ZIP化（`packaging`: `SkillScaffolder`, `SkillPackager`）
  - サンドボックス & 多層評価・Tier昇格（`evaluation`: `ContractTestRunner`, `SimulationEvalRunner`, `CascadeTestRunner`, `LocalWorkspaceEnv`）
  - Google ADK 2.0 / MCP アダプタ（`adk`: `create_adk_skill_toolset`, `EddSkillToolset` / `mcp`: `create_mcp_server`）
  - 統合 CLI（`cli`: `edd run/init/validate/package/eval/tier-gate/diagnose/optimize`）
  ※ 他プロジェクトに `pip install` された環境でも単独で完全動作するよう、パッケージ内部は外部プロジェクト固有パスへの暗黙依存を持たない完全自己完結設計とします。

* **規約駆動・ゼロ依存スキル資産層 (`src/skills/<skill>/`)**:
  - スキル内のスクリプトは `edd_agent_tools` を直接 Python import せず、Python 標準ライブラリと CLI/IO 規約（`--help`、引数、標準入出力）のみで完結するゼロ依存設計とします。
  - スキル単体（または ZIP）を別プロジェクト（Claude Code, Cursor, Antigravity, Google ADK 等）にコピーするだけで即座に動作するポータビリティを保証します。
  - メタスキル（`skill-creator`, `skill-evolver`）のスクリプトは、共通処理を再実装（重複）せず、統合 CLI（`edd`）をプロセス境界 API として呼び出す薄型クライアントとします。

---

## 2. 自己進化のための変更境界ルール (Mutation Boundaries)
エージェントがスキルを進化・修復する際は、以下の境界線を厳格に遵守してください：

* **🟢 エージェント変更可能領域 (Mutable Zone: 自己進化対象)**:
  - `SKILL.md` (手順、プロンプト、意思決定ツリー、トリガー条件、When NOT to use)
  - `scripts/` 配下の個別ドメインロジック（ビジネスルール・変換関数）
  - `references/` (ドメイン知識、スキーマ仕様)
  - `assets/` (出力用テンプレート・素材)
  - `tests/` (契約テスト、シミュレーション評価データセット)
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