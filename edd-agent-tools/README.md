# edd-agent-tools

EDD（評価駆動開発: Evaluation-Driven Development）による自律型 AI エージェント、および Google ADK 2.0 / Anthropic 標準（Markdown-First & Progressive Disclosure）スキルの開発・運用・自己進化をサポートするためのフルスタック基盤パッケージ。

---

## 1. 主な機能と特徴

*   **Clean Layered Architecture (`core`, `validation`, `packaging`, `evaluation`, `adk`, `mcp`, `cli`)**
    単一真実源のドメインモデル（`core` / `SkillPackage`, `SkillTests`, `SkillsState`）、AST静的検証リンター（`validation` / `SkillValidator`）、ZIPパッケージング＆スキャフォールド（`packaging` / `SkillPackager`, `SkillScaffolder`）、契約テスト・多層評価・診断・自己修復（`evaluation`）、Google ADK 2.0 純正連携（`adk` / `EddSkillToolset`, `EddSkillRegistry`）、FastMCP 連携（`mcp`）、統合 CLI（`cli`）を明確に責務分離。
*   **Markdown-First & Progressive Disclosure リソース管理 (`SkillPackage`, `SkillSpec`, `SkillsState`)**
    `SKILL.md` を単一真実源とし、`scripts/`（実行用）、`references/`（知識用）、`assets/`（素材用）、`examples/`（使用例用）のリソース分離を安全にロード・管理するドメインクラスと DAG 依存関係グラフ検証を提供。他プロジェクトへの配布時にもパスに依存しない Zero-Hardcoding 設計。
*   **Google ADK 2.0 ネイティブ完全統合 (`google.adk.skills`, `SkillToolset`, `AgentEvaluator`, `TrajectoryEvaluator`, `ResponseEvaluator`, `EvalConfig`)**
    - Google ADK 純正の `SkillToolset` による Progressive Disclosure ライフサイクル（`list_skills` ➔ `load_skill` ➔ `load_skill_resource` ➔ `run_skill_script` ➔ `search_skills`）を完全採用。
    - プライベート属性アクセス（`_tools` 等）や手動キーワード照合による偽ルーブリック判定を完全排除。ADK 2.0 公式公開API（`await toolset.get_tools()`）および公式評価器（`TrajectoryEvaluator`, `ResponseEvaluator`, `RubricBasedFinalResponseQualityV1Evaluator`）に一本化。
    - `AgentEvaluator` の例外ログ構造解析により各テストケースごとの合否を集計。Google ADK 2.0 公式 `test_config.json`（`EvalConfig`）による自動探索と `match_type: "IN_ORDER"` 標準配備。
*   **決定論的サンドボックス隔離環境 (`WorkspaceEnvProtocol`, `LocalWorkspaceEnv`)**
    コードやテスト実行による環境破壊を防ぐため、OS 一時領域への複製、Git ロールバック、および差分抽出機能を提供。
*   **多層EDD評価フレームワーク & Tier昇格ゲートキーパー (`ContractTestRunner`, `SimulationEvalRunner`, `AdkEvalAdapter`, `CascadeTestRunner`)**
    単一真実源（SSOT）である `{skill_name}.test.json`（Google ADK 2.0 公式 `EvalSet`、3正例＋3負例）に基づき、契約テスト（CLI Black-box、`pass^k` 連続実行）、トリガー精度、ツール軌跡（`EXACT` / `IN_ORDER` / `ANY_ORDER`）、共存ベンチマーク（`CoLoadedEvalRunner`）、連鎖回帰テストを一元管理。
*   **失敗診断 & 自己進化エンジン (`SkillDiagnoser`, `SkillOptimizer`)**
    テスト失敗ログを構造的に解析し、根本原因（spec / script / test / reference / example）の特定と自律的な修復ループ・Tier昇格を実現。
*   **統合 CLI (`edd`) & FastMCP サーバー (`edd-agent-mcp`)**
    エージェントが CLI-as-an-API として呼び出せる統合コマンドラインツール、および Claude Code / Antigravity IDE 向け MCP リソース・ツールを提供。

---

## 2. 詳細設計書インデックス (Detailed Documents)

*   **[design_philosophy.md](src/edd_agent_tools/docs/design_philosophy.md)**: 全体設計思想・Two-Tier アーキテクチャ・フォルダ構成規約。
*   **[test_architecture.md](src/edd_agent_tools/docs/test_architecture.md)**: Google ADK 2.0 公式 EvalSet SSOT および多層テスト評価アーキテクチャ仕様。
*   **[eval_design.md](src/edd_agent_tools/docs/eval_design.md)**: 仮想環境サンドボックスとシミュレーション評価・ADK 公式評価連携の設計仕様。
*   **[progressive_disclosure.md](src/edd_agent_tools/docs/progressive_disclosure.md)**: リソース分離とProgressive Disclosure標準規約。
*   **[prompt_syntax.md](src/edd_agent_tools/docs/prompt_syntax.md)**: Imperative文体規約とFrontmatter仕様。
*   **[skill_patterns.md](src/edd_agent_tools/docs/skill_patterns.md)**: 4大スキルパターンの設計ガイド。
*   **[sandbox_design.md](src/edd_agent_tools/docs/sandbox_design.md)**: 決定論的サンドボックス仮想環境、Git高速ロールバック、および成果物差分抽出の設計仕様。

---

## 3. インストールと統合 CLI (`edd`)

```bash
pip install -e edd-agent-tools

# 統合 CLI (edd) - 動的ディスパッチによるスキルの直接実行
edd run case-converter --to camel "hello_world"
# またはスキル名を直接サブコマンドとして指定可能 (Git プラグイン方式)
edd case-converter --to camel "hello_world"

# スキルライフサイクル管理
edd init my-skill --pattern workflow
edd validate src/skills/my-skill
edd package src/skills/my-skill --out dist
edd list

# Google ADK 2.0 公式評価・契約テスト
edd eval my-skill                      # デフォルト総合評価 (ADK 2.0 Native AgentEvaluator)
edd eval my-skill --coverage           # 白書 4大 Eval Coverage チェックリスト
edd eval my-skill --type contract -k 3 # pass^3 持続的信頼性契約テスト
edd adk-eval my-skill                  # AgentEvaluator 直接実行
edd adk-eval my-skill --cli            # 公式 adk eval CLI サブプロセス直接実行

# Tier 昇格・失敗診断・一括最適化
edd tier-gate my-skill --tier 1
edd tier-gate my-skill --tier 3 --yes  # Human Sign-off 承認付き Tier 3 昇格
edd diagnose my-skill
edd optimize my-skill --tier 1

# トレースからのスキル自動抽出
edd harvest-trace path/to/trace.json my-harvested-skill

# MCP サーバー起動
edd-agent-mcp
```
